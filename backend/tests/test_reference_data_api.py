import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def test_statuses_readable_by_any_authenticated_user(api_client, authed, make_user, reference):
    employee = make_user("emp-ref", "employee")
    response = authed(employee).get("/api/v1/reference-data/statuses/")
    assert response.status_code == 200
    codes = {row["code"] for row in response.json()["results"]}
    assert {"draft", "in_stock", "assigned", "disposed"} <= codes


def test_reference_write_forbidden_for_non_admin(api_client, authed, make_user, reference):
    operator = make_user("op-ref", "operator")
    response = authed(operator).post(
        "/api/v1/reference-data/departments/",
        {"code": "NEW", "name": "New Dept"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_reference_write_allowed_for_admin(api_client, authed, make_user, reference):
    admin = make_user("admin-ref", "system_admin")
    response = authed(admin).post(
        "/api/v1/reference-data/departments/",
        {"code": "NEW", "name": "New Dept"},
        format="json",
    )
    assert response.status_code == 201, response.json()


def test_transition_rules_listed(api_client, authed, make_user, reference):
    operator = make_user("op-rules", "operator")
    response = authed(operator).get("/api/v1/reference-data/transition-rules/")
    assert response.status_code == 200
    rules = response.json()["results"]
    assert any(
        rule["from_status"] == "in_stock" and rule["to_status"] == "assigned" for rule in rules
    )
