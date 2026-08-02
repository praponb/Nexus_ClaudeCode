"""Maintenance records (FR-011) and finance field gating (FR-012/D-06)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _operator(make_user, reference):
    return make_user("mx-operator", "operator", scope_department=reference.department)


def test_create_record_puts_asset_under_maintenance(
    api_client, make_user, make_asset, workflow_reference
):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("MX-001")
    api_client.force_authenticate(operator)
    response = api_client.post(
        "/api/v1/maintenance/",
        {
            "asset": str(asset.uuid),
            "maintenance_type": str(workflow_reference.repair.uuid),
            "issue": "Broken hinge",
            "provider": "Acme Repair",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    asset.refresh_from_db()
    assert asset.status.code == "under_maintenance"
    # Operators do not see the finance-restricted cost field (FR-011/D-06).
    assert "cost" not in response.json()


def test_create_second_open_record_conflicts(api_client, make_user, make_asset, workflow_reference):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("MX-002")
    api_client.force_authenticate(operator)
    payload = {
        "asset": str(asset.uuid),
        "maintenance_type": str(workflow_reference.repair.uuid),
    }
    assert api_client.post("/api/v1/maintenance/", payload, format="json").status_code == 201
    conflict = api_client.post("/api/v1/maintenance/", payload, format="json")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "MAINTENANCE_ALREADY_OPEN"


def test_manager_sees_and_sets_cost(api_client, make_user, make_asset, workflow_reference):
    manager = make_user("mx-manager", "asset_manager")
    asset = make_asset("MX-003")
    api_client.force_authenticate(manager)
    response = api_client.post(
        "/api/v1/maintenance/",
        {
            "asset": str(asset.uuid),
            "maintenance_type": str(workflow_reference.repair.uuid),
            "cost": {"amount": "250.00", "currency": "USD"},
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["cost"] == {"amount": "250.00", "currency": "USD"}


def test_complete_record_returns_asset_to_service(
    api_client, make_user, make_asset, workflow_reference
):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("MX-004")
    api_client.force_authenticate(operator)
    created = api_client.post(
        "/api/v1/maintenance/",
        {
            "asset": str(asset.uuid),
            "maintenance_type": str(workflow_reference.repair.uuid),
        },
        format="json",
    )
    record_uuid = created.json()["uuid"]
    completed = api_client.post(
        f"/api/v1/maintenance/{record_uuid}/complete/",
        {"result": "Replaced hinge", "next_due": "2027-06-01"},
        format="json",
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    asset.refresh_from_db()
    assert asset.status.code == "available"
    assert asset.last_maintenance_date is not None
    assert str(asset.next_maintenance_due) == "2027-06-01"

    again = api_client.post(f"/api/v1/maintenance/{record_uuid}/complete/", {}, format="json")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "MAINTENANCE_NOT_OPEN"


def test_employee_cannot_create_maintenance(api_client, make_user, make_asset, workflow_reference):
    employee = make_user("mx-employee", "employee")
    asset = make_asset("MX-005", custodian=employee)
    api_client.force_authenticate(employee)
    response = api_client.post(
        "/api/v1/maintenance/",
        {
            "asset": str(asset.uuid),
            "maintenance_type": str(workflow_reference.repair.uuid),
        },
        format="json",
    )
    assert response.status_code == 403


def test_maintenance_create_is_idempotent(api_client, make_user, make_asset, workflow_reference):
    from apps.maintenance.models import MaintenanceRecord

    operator = _operator(make_user, workflow_reference)
    asset = make_asset("MX-006")
    api_client.force_authenticate(operator)
    payload = {
        "asset": str(asset.uuid),
        "maintenance_type": str(workflow_reference.repair.uuid),
        "issue": "Intermittent fault",
    }
    first = api_client.post(
        "/api/v1/maintenance/", payload, format="json", HTTP_IDEMPOTENCY_KEY="mx-key-1"
    )
    assert first.status_code == 201
    replay = api_client.post(
        "/api/v1/maintenance/", payload, format="json", HTTP_IDEMPOTENCY_KEY="mx-key-1"
    )
    assert replay.status_code == 201
    assert replay.json()["uuid"] == first.json()["uuid"]
    assert MaintenanceRecord.objects.filter(asset=asset).count() == 1


def test_maintenance_list_scoped_to_visible_assets(
    api_client, make_user, make_asset, workflow_reference
):
    from apps.maintenance.models import MaintenanceRecord

    operator = _operator(make_user, workflow_reference)
    visible = make_asset("MX-007")
    hidden = make_asset("MX-008", department=workflow_reference.other_department)
    MaintenanceRecord.objects.create(
        asset=visible, maintenance_type=workflow_reference.repair, issue="A"
    )
    MaintenanceRecord.objects.create(
        asset=hidden, maintenance_type=workflow_reference.repair, issue="B"
    )
    api_client.force_authenticate(operator)
    response = api_client.get("/api/v1/maintenance/")
    assert response.status_code == 200
    tags = {row["asset"]["tag"] for row in response.json()["results"]}
    assert "MX-007" in tags
    assert "MX-008" not in tags
