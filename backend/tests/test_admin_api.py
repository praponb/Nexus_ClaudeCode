"""User administration (FR-027) and audit query API (FR-025 read path)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def test_admin_lists_and_updates_users(api_client, make_user, reference):
    from apps.audit.models import AuditEvent

    admin = make_user("adm-admin", "system_admin")
    target = make_user("adm-target", "employee")
    api_client.force_authenticate(admin)

    listed = api_client.get("/api/v1/admin/users/")
    assert listed.status_code == 200
    usernames = [row["username"] for row in listed.json()["results"]]
    assert "adm-target" in usernames

    updated = api_client.patch(
        f"/api/v1/admin/users/{target.uuid}/",
        {
            "role": "operator",
            "scopes": [{"scope_type": "department", "department": str(reference.department.uuid)}],
        },
        format="json",
    )
    assert updated.status_code == 200, updated.json()
    assert updated.json()["role"] == "operator"
    assert updated.json()["scopes"][0]["department"]["uuid"] == str(reference.department.uuid)
    assert AuditEvent.objects.filter(action="admin.user.update").exists()


def test_admin_endpoints_require_admin(api_client, make_user, reference):
    operator = make_user("adm-op", "operator", scope_department=reference.department)
    target = make_user("adm-target-2", "employee")
    api_client.force_authenticate(operator)
    assert api_client.get("/api/v1/admin/users/").status_code == 403
    assert (
        api_client.patch(
            f"/api/v1/admin/users/{target.uuid}/", {"role": "operator"}, format="json"
        ).status_code
        == 403
    )


def test_final_admin_cannot_be_demoted_or_deactivated(api_client, make_user, reference):
    admin = make_user("adm-solo", "system_admin")
    api_client.force_authenticate(admin)

    demoted = api_client.patch(
        f"/api/v1/admin/users/{admin.uuid}/", {"role": "employee"}, format="json"
    )
    assert demoted.status_code == 409
    assert demoted.json()["error"]["code"] == "LAST_ADMIN"

    deactivated = api_client.patch(
        f"/api/v1/admin/users/{admin.uuid}/", {"is_active": False}, format="json"
    )
    assert deactivated.status_code == 409

    # With a second active administrator present, the change is allowed.
    make_user("adm-second", "system_admin")
    allowed = api_client.patch(
        f"/api/v1/admin/users/{admin.uuid}/", {"role": "auditor"}, format="json"
    )
    assert allowed.status_code == 200


def test_admin_rejects_non_editable_fields(api_client, make_user, reference):
    admin = make_user("adm-admin-2", "system_admin")
    target = make_user("adm-target-3", "employee")
    api_client.force_authenticate(admin)
    response = api_client.patch(
        f"/api/v1/admin/users/{target.uuid}/", {"password": "x", "username": "y"}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.json()["error"]["field_errors"]


def test_audit_events_queryable_by_authorized_users(api_client, make_user, make_asset, reference):
    admin = make_user("adm-admin-3", "system_admin")
    auditor = make_user("adm-auditor", "auditor")
    employee = make_user("adm-employee", "employee")

    api_client.force_authenticate(admin)
    asset = make_asset("AUD-001")
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/notes/", {"body": "Audit trail check."}, format="json"
    )

    api_client.force_authenticate(auditor)
    response = api_client.get("/api/v1/admin/audit-events/", {"action": "note.create"})
    assert response.status_code == 200
    rows = response.json()["results"]
    assert len(rows) == 1
    assert rows[0]["action"] == "note.create"
    assert rows[0]["target_uuid"] == str(asset.uuid)

    filtered = api_client.get("/api/v1/admin/audit-events/", {"target_uuid": str(asset.uuid)})
    assert len(filtered.json()["results"]) >= 1

    api_client.force_authenticate(employee)
    assert api_client.get("/api/v1/admin/audit-events/").status_code == 403
