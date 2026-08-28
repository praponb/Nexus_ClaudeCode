"""Brute-force and second-factor controls for a publicly reachable sign-in
(NFR-007, design section 12).

The site is open to the internet, so the login endpoint is the only gate. These
cover the two axes that guard it: a per-account failure budget that a
distributed attack cannot sidestep, and TOTP for privileged roles.
"""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")
pytest.importorskip("pyotp")

from tests.conftest import TEST_PASSWORD  # noqa: E402

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_lockout_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def _login(client, username, password, **extra):
    return client.post(
        "/api/v1/auth/login/",
        {"username": username, "password": password},
        format="json",
        **extra,
    )


# -- Per-account lockout -------------------------------------------------------


def test_lockout_survives_rotating_client_ips(api_client, make_user, settings):
    """The point of the per-account counter: per-IP throttling cannot do this.

    Every attempt arrives from a different address, so LoginThrottle's per-IP
    bucket is never filled -- only the per-username budget stops it.
    """
    settings.LOGIN_LOCKOUT_THRESHOLD = 5
    make_user("locktarget", "operator")

    for attempt in range(5):
        response = _login(
            api_client, "locktarget", "wrong", HTTP_CF_CONNECTING_IP=f"203.0.113.{attempt}"
        )
        assert response.status_code == 401

    blocked = _login(api_client, "locktarget", "wrong", HTTP_CF_CONNECTING_IP="198.51.100.9")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_lockout_blocks_even_the_correct_password(api_client, make_user, settings):
    """Otherwise an attacker who eventually guesses right still gets in."""
    settings.LOGIN_LOCKOUT_THRESHOLD = 3
    make_user("locked-out", "operator")
    for _ in range(3):
        assert _login(api_client, "locked-out", "wrong").status_code == 401
    assert _login(api_client, "locked-out", TEST_PASSWORD).status_code == 429


def test_successful_login_clears_the_counter(api_client, make_user, settings):
    """A user who mistypes once then succeeds must not accumulate toward a lock."""
    from apps.core import login_guard

    settings.LOGIN_LOCKOUT_THRESHOLD = 5
    make_user("butterfingers", "operator")
    assert _login(api_client, "butterfingers", "wrong").status_code == 401
    assert login_guard.failure_count("butterfingers") == 1
    assert _login(api_client, "butterfingers", TEST_PASSWORD).status_code == 200
    assert login_guard.failure_count("butterfingers") == 0


def test_unknown_usernames_are_counted_so_lockout_does_not_leak_existence(api_client, settings):

    settings.LOGIN_LOCKOUT_THRESHOLD = 2
    assert _login(api_client, "no-such-person", "wrong").status_code == 401
    assert _login(api_client, "no-such-person", "wrong").status_code == 401
    # Same 429 an existing account would give: the response cannot be used to
    # tell real usernames from invented ones.
    assert _login(api_client, "no-such-person", "wrong").status_code == 429


def test_public_demo_account_is_never_locked(api_client, make_user, settings):
    """Its password is published, and locking it would deny every visitor."""
    settings.LOGIN_LOCKOUT_THRESHOLD = 3
    settings.LOGIN_LOCKOUT_EXEMPT_USERNAMES = ["demo"]
    make_user("demo", "viewer")
    for _ in range(6):
        assert _login(api_client, "demo", "wrong").status_code == 401
    assert _login(api_client, "demo", TEST_PASSWORD).status_code == 200


# -- TOTP second factor --------------------------------------------------------


def _totp_now(secret):
    import pyotp

    return pyotp.TOTP(secret).now()


def _rewind_spent_step(user):
    """Simulate time passing since the last accepted code.

    TOTP codes are one-per-30s-step; tests run inside a single step, so without
    this a follow-up sign-in would present an already-spent code.
    """
    device = user.totp_device
    device.refresh_from_db()
    device.last_used_step = (device.last_used_step or 0) - 5
    device.save(update_fields=["last_used_step"])


def test_privileged_login_does_not_authenticate_on_password_alone(api_client, make_user, settings):
    """The whole point: a stolen admin password must not be enough."""
    settings.MFA_REQUIRED_ROLES = ["system_admin"]
    make_user("root-user", "system_admin")

    response = _login(api_client, "root-user", TEST_PASSWORD)
    assert response.status_code == 200
    assert response.json() == {"mfa_required": True, "stage": "setup"}
    # Still anonymous: no session was established by the password step.
    assert api_client.get("/api/v1/auth/me/").status_code == 401


def test_enrolment_then_verification_completes_sign_in(api_client, make_user, settings):
    settings.MFA_REQUIRED_ROLES = ["system_admin"]
    user = make_user("root-enrol", "system_admin")

    assert _login(api_client, "root-enrol", TEST_PASSWORD).json()["stage"] == "setup"
    setup = api_client.post("/api/v1/auth/2fa/setup/", {}, format="json")
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["qr_svg"].startswith("<?xml") or "<svg" in setup.json()["qr_svg"]

    confirmed = api_client.post(
        "/api/v1/auth/2fa/confirm/", {"code": _totp_now(secret)}, format="json"
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["user"]["username"] == "root-enrol"
    assert len(confirmed.json()["recovery_codes"]) == 10
    assert api_client.get("/api/v1/auth/me/").status_code == 200

    # Second sign-in now takes the verify path. Wind the spent step back so the
    # next code counts as a later one -- otherwise this reuses the very code
    # enrolment just consumed, which is a replay and correctly refused.
    _rewind_spent_step(user)
    api_client.post("/api/v1/auth/logout/", {}, format="json")
    assert _login(api_client, "root-enrol", TEST_PASSWORD).json()["stage"] == "verify"
    assert api_client.get("/api/v1/auth/me/").status_code == 401
    verified = api_client.post(
        "/api/v1/auth/2fa/verify/", {"code": _totp_now(secret)}, format="json"
    )
    assert verified.status_code == 200
    assert api_client.get("/api/v1/auth/me/").status_code == 200
    assert user.totp_device.is_confirmed


def test_wrong_code_does_not_sign_in(api_client, make_user, settings):
    settings.MFA_REQUIRED_ROLES = ["system_admin"]
    make_user("root-badcode", "system_admin")
    _login(api_client, "root-badcode", TEST_PASSWORD)
    secret = api_client.post("/api/v1/auth/2fa/setup/", {}, format="json").json()["secret"]
    api_client.post("/api/v1/auth/2fa/confirm/", {"code": _totp_now(secret)}, format="json")
    api_client.post("/api/v1/auth/logout/", {}, format="json")

    _login(api_client, "root-badcode", TEST_PASSWORD)
    bad = api_client.post("/api/v1/auth/2fa/verify/", {"code": "000000"}, format="json")
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "MFA_INVALID_CODE"
    assert api_client.get("/api/v1/auth/me/").status_code == 401


def test_a_code_cannot_be_replayed(api_client, make_user, settings):
    """TOTP codes stay valid for a whole step; an observed one must not be reusable."""
    settings.MFA_REQUIRED_ROLES = ["system_admin"]
    make_user("root-replay", "system_admin")
    _login(api_client, "root-replay", TEST_PASSWORD)
    secret = api_client.post("/api/v1/auth/2fa/setup/", {}, format="json").json()["secret"]
    code = _totp_now(secret)
    api_client.post("/api/v1/auth/2fa/confirm/", {"code": code}, format="json")
    api_client.post("/api/v1/auth/logout/", {}, format="json")

    _login(api_client, "root-replay", TEST_PASSWORD)
    replayed = api_client.post("/api/v1/auth/2fa/verify/", {"code": code}, format="json")
    assert replayed.status_code == 400
    assert api_client.get("/api/v1/auth/me/").status_code == 401


def test_recovery_code_works_once(api_client, make_user, settings):
    settings.MFA_REQUIRED_ROLES = ["system_admin"]
    make_user("root-recovery", "system_admin")
    _login(api_client, "root-recovery", TEST_PASSWORD)
    secret = api_client.post("/api/v1/auth/2fa/setup/", {}, format="json").json()["secret"]
    codes = api_client.post(
        "/api/v1/auth/2fa/confirm/", {"code": _totp_now(secret)}, format="json"
    ).json()["recovery_codes"]
    api_client.post("/api/v1/auth/logout/", {}, format="json")

    _login(api_client, "root-recovery", TEST_PASSWORD)
    first = api_client.post("/api/v1/auth/2fa/verify/", {"recovery_code": codes[0]}, format="json")
    assert first.status_code == 200
    assert first.json()["recovery_codes_remaining"] == 9
    api_client.post("/api/v1/auth/logout/", {}, format="json")

    _login(api_client, "root-recovery", TEST_PASSWORD)
    reused = api_client.post("/api/v1/auth/2fa/verify/", {"recovery_code": codes[0]}, format="json")
    assert reused.status_code == 400


def test_second_factor_endpoints_reject_callers_with_no_pending_sign_in(api_client):
    """Without the password step these are unauthenticated strangers."""
    for path in ("setup", "confirm", "verify"):
        response = api_client.post(f"/api/v1/auth/2fa/{path}/", {"code": "123456"}, format="json")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "MFA_PENDING_EXPIRED"


def test_roles_without_the_requirement_sign_in_normally(api_client, make_user, settings):
    settings.MFA_REQUIRED_ROLES = ["system_admin"]
    make_user("plain-viewer", "viewer")
    response = _login(api_client, "plain-viewer", TEST_PASSWORD)
    assert response.status_code == 200
    assert "mfa_required" not in response.json()
    assert api_client.get("/api/v1/auth/me/").status_code == 200
