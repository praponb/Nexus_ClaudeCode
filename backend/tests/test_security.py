"""Security controls carried over from the Cycle-1 QA blocked list:
CSRF enforcement, session rotation on login, login rate limiting, response
security headers, CORS allowlist behaviour — plus combined filter/sort
coverage (FR-005) and reference-data deactivate semantics (BR-004, DEF-006).
"""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from tests.conftest import TEST_PASSWORD  # noqa: E402

pytestmark = pytest.mark.django_db


def _asset_payload(reference):
    return {
        "name": "CSRF laptop",
        "category": str(reference.category.uuid),
        "status": str(reference.in_stock.uuid),
        "condition": str(reference.condition.uuid),
        "department": str(reference.department.uuid),
        "location": str(reference.location.uuid),
        "acquisition_type": "purchased",
    }


def test_csrf_rejected_without_token(make_user, reference):
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=True)
    make_user("csrf-user", "operator")
    assert client.login(username="csrf-user", password=TEST_PASSWORD)
    response = client.post("/api/v1/assets/", _asset_payload(reference), format="json")
    assert response.status_code == 403


def test_csrf_accepted_with_token(make_user, reference):
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=True)
    make_user("csrf-user-2", "operator")
    assert client.login(username="csrf-user-2", password=TEST_PASSWORD)
    client.get("/api/v1/auth/csrf/")
    token = client.cookies["csrftoken"].value
    response = client.post(
        "/api/v1/assets/", _asset_payload(reference), format="json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 201, response.json()


def test_session_rotates_on_login(api_client, make_user):
    make_user("rotate-me", "employee")
    session = api_client.session
    session.save()
    old_key = session.session_key
    api_client.cookies["sessionid"] = old_key
    response = api_client.post(
        "/api/v1/auth/login/",
        {"username": "rotate-me", "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    new_cookie = api_client.cookies.get("sessionid")
    assert new_cookie is not None
    assert new_cookie.value != old_key


def test_login_rate_limited(api_client, make_user, monkeypatch):
    from django.core.cache import cache

    from apps.accounts.views import LoginThrottle

    # DRF reads THROTTLE_RATES into a class attribute at import time, so the
    # rate is patched directly on the throttle class for this test.
    monkeypatch.setattr(LoginThrottle, "THROTTLE_RATES", {"login": "3/minute"})
    cache.clear()
    make_user("throttled-user", "operator")
    for _ in range(3):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": "throttled-user", "password": "wrong-password"},
            format="json",
        )
        assert response.status_code == 401
    blocked = api_client.post(
        "/api/v1/auth/login/",
        {"username": "throttled-user", "password": "wrong-password"},
        format="json",
    )
    assert blocked.status_code == 429
    error = blocked.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert error["retryable"] is True


def test_security_headers_present(api_client):
    response = api_client.get("/api/v1/health/live/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert "Content-Security-Policy" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"


def test_cors_origin_not_reflected_for_unlisted_origin(api_client):
    response = api_client.get("/api/v1/health/live/", HTTP_ORIGIN="https://evil.example.com")
    assert "Access-Control-Allow-Origin" not in response.headers


def test_combined_filters_and_ordering(api_client, make_user, make_asset, reference):
    operator = make_user("filter-op", "operator", scope_department=reference.department)
    make_asset("FLT-001", name="Alpha")
    make_asset("FLT-002", name="Zulu")
    make_asset("FLT-003", name="Mike", status=reference.assigned)
    api_client.force_authenticate(operator)

    response = api_client.get(
        "/api/v1/assets/",
        {"status_code": "in_stock", "category": str(reference.category.uuid), "ordering": "-name"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"count", "next", "previous", "results"}
    names = [row["name"] for row in body["results"]]
    assert names == ["Zulu", "Alpha"]


def test_assigned_boolean_filter(api_client, make_user, make_asset, reference):
    from apps.assignments.models import Assignment

    operator = make_user("filter-op-2", "operator", scope_department=reference.department)
    assigned_asset = make_asset("FLT-010")
    make_asset("FLT-011")
    Assignment.objects.create(asset=assigned_asset, custodian=operator)
    api_client.force_authenticate(operator)

    response = api_client.get("/api/v1/assets/", {"assigned": "true"})
    tags = [row["tag"] for row in response.json()["results"]]
    assert tags == ["FLT-010"]
    response = api_client.get("/api/v1/assets/", {"assigned": "false"})
    tags = [row["tag"] for row in response.json()["results"]]
    assert tags == ["FLT-011"]


def test_reference_data_delete_deactivates_instead_of_deleting(api_client, make_user, reference):
    from apps.audit.models import AuditEvent
    from apps.reference_data.models import Department

    admin = make_user("ref-admin", "system_admin")
    api_client.force_authenticate(admin)
    url = f"/api/v1/reference-data/departments/{reference.department.uuid}/"
    response = api_client.delete(url)
    assert response.status_code == 200
    reference.department.refresh_from_db()
    assert reference.department.active is False
    # BR-004: the row is preserved; a repeat DELETE is idempotent.
    assert Department.objects.filter(pk=reference.department.pk).exists()
    repeat = api_client.delete(url)
    assert repeat.status_code == 200
    assert repeat.json()["active"] is False
    assert AuditEvent.objects.filter(action="reference.department.deactivate").exists()


def test_reference_data_write_requires_admin(api_client, make_user, reference):
    operator = make_user("ref-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    url = f"/api/v1/reference-data/departments/{reference.department.uuid}/"
    assert api_client.delete(url).status_code == 403
    created = api_client.post(
        "/api/v1/reference-data/departments/", {"code": "x", "name": "X"}, format="json"
    )
    assert created.status_code == 403


def test_base_settings_ship_production_safe_throttle_defaults():
    """base.py must never inherit the dev ceilings that local.py/test.py set.

    Regression guard: a permissive `login` rate in base.py silently disables
    brute-force protection in production while making the local/test overrides
    look like harmless no-ops, which is exactly how it went unnoticed before.
    """
    from config.settings import base

    count, _, period = base.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"].partition("/")
    assert period == "minute"
    assert int(count) <= 20


def test_base_settings_use_a_shared_cache_for_throttle_counters():
    """DRF stores throttle counters in the default cache (design section 12).

    LocMemCache is per-process, so under the production image's
    `gunicorn --workers 3` it would triple every configured rate and reset the
    counters on each deploy.
    """
    from config.settings import base

    assert "locmem" not in base.CACHES["default"]["BACKEND"].lower()


def test_login_throttle_ignores_spoofed_forwarded_for(api_client, make_user, monkeypatch):
    """A rotating X-Forwarded-For must not hand out fresh throttle buckets.

    DRF's own get_ident() derives the bucket from the whole X-Forwarded-For
    header when NUM_PROXIES is unset, so varying it defeated the rate limit
    entirely. ScopedSimpleRateThrottle uses apps.core.client_ip instead.
    """
    from django.core.cache import cache

    from apps.accounts.views import LoginThrottle

    monkeypatch.setattr(LoginThrottle, "THROTTLE_RATES", {"login": "3/minute"})
    cache.clear()
    make_user("xff-victim", "operator")
    for attempt in range(3):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": "xff-victim", "password": "wrong-password"},
            format="json",
            HTTP_X_FORWARDED_FOR=f"10.0.0.{attempt}",
        )
        assert response.status_code == 401
    blocked = api_client.post(
        "/api/v1/auth/login/",
        {"username": "xff-victim", "password": "wrong-password"},
        format="json",
        HTTP_X_FORWARDED_FOR="203.0.113.99",
    )
    assert blocked.status_code == 429


def test_client_ip_rejects_non_ip_values(settings):
    """AuditEvent.ip_address is a PostgreSQL inet column.

    Caller-supplied junk used to reach it via X-Forwarded-For, turning a failed
    login into a DataError (an unauthenticated 500).
    """
    from django.test import RequestFactory

    from apps.core.client_ip import client_ip

    settings.TRUSTED_CLIENT_IP_HEADER = "HTTP_CF_CONNECTING_IP"
    request = RequestFactory().get("/")

    request.META["HTTP_CF_CONNECTING_IP"] = "not-an-ip-address"
    request.META["REMOTE_ADDR"] = "198.51.100.7"
    assert client_ip(request) == "198.51.100.7"

    request.META["HTTP_CF_CONNECTING_IP"] = "203.0.113.5"
    assert client_ip(request) == "203.0.113.5"

    request.META["HTTP_CF_CONNECTING_IP"] = "junk"
    request.META["REMOTE_ADDR"] = "also-junk"
    assert client_ip(request) is None


def test_client_ip_ignores_forwarded_for_when_no_trusted_header(settings):
    from django.test import RequestFactory

    from apps.core.client_ip import client_ip

    settings.TRUSTED_CLIENT_IP_HEADER = ""
    request = RequestFactory().get("/")
    request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4"
    request.META["REMOTE_ADDR"] = "198.51.100.7"
    assert client_ip(request) == "198.51.100.7"


def test_asset_search_is_throttled(api_client, make_user, monkeypatch):
    """Design section 12 requires a rate limit on search/scan lookup."""
    from django.core.cache import cache

    from apps.assets.views import SearchThrottle

    monkeypatch.setattr(SearchThrottle, "THROTTLE_RATES", {"search": "2/minute"})
    cache.clear()
    api_client.force_authenticate(make_user("search-user", "operator"))
    for _ in range(2):
        assert api_client.get("/api/v1/search/assets/?q=abc").status_code == 200
    assert api_client.get("/api/v1/search/assets/?q=abc").status_code == 429
