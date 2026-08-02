import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from tests.conftest import TEST_PASSWORD  # noqa: E402

pytestmark = pytest.mark.django_db


def test_csrf_endpoint_sets_cookie(api_client):
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    assert "csrftoken" in response.cookies


def test_login_success_returns_user_and_audits(api_client, make_user):
    from apps.audit.models import AuditEvent

    make_user("operator1", "operator")
    response = api_client.post(
        "/api/v1/auth/login/",
        {"username": "operator1", "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "operator"
    assert "asset.create" in body["user"]["capabilities"]
    assert AuditEvent.objects.filter(action="auth.login", outcome="success").exists()


def test_login_failure_is_generic_and_audited(api_client, make_user):
    from apps.audit.models import AuditEvent

    make_user("operator2", "operator")
    response = api_client.post(
        "/api/v1/auth/login/",
        {"username": "operator2", "password": "wrong-password"},
        format="json",
    )
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "AUTHENTICATION_FAILED"
    assert error["message"] == "Invalid username or password."
    assert error["correlation_id"]
    assert AuditEvent.objects.filter(action="auth.login", outcome="failure").exists()


def test_login_unknown_user_same_message(api_client):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"username": "does-not-exist", "password": "whatever"},
        format="json",
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid username or password."


def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_logout_invalidates_session(api_client, make_user):
    user = make_user("employee1", "employee")
    api_client.force_login(user)
    assert api_client.get("/api/v1/auth/me/").status_code == 200
    response = api_client.post("/api/v1/auth/logout/")
    assert response.status_code == 204
    assert api_client.get("/api/v1/auth/me/").status_code == 401


def test_correlation_id_echoed(api_client, make_user):
    user = make_user("auditor1", "auditor")
    api_client.force_authenticate(user)
    response = api_client.get(
        "/api/v1/auth/me/", HTTP_X_CORRELATION_ID="3eeab8b7-6c83-4dbe-b62b-9dbdb3cb8dab"
    )
    assert response.headers["X-Correlation-ID"] == "3eeab8b7-6c83-4dbe-b62b-9dbdb3cb8dab"
