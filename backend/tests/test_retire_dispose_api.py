"""Retirement, disposal, and reopen (FR-014, J-5; BR-006 blockers)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _operator(make_user, reference, username="fr14-operator"):
    return make_user(username, "operator", scope_department=reference.department)


def test_retire_sets_status_and_date(api_client, make_user, make_asset, disposal_reference):
    operator = _operator(make_user, disposal_reference)
    asset = make_asset("FR14-001")
    api_client.force_authenticate(operator)
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/retire/", {"reason": "End of life"}, format="json"
    )
    assert response.status_code == 200, response.json()
    asset.refresh_from_db()
    assert asset.status.code == "retired"
    assert asset.retirement_date is not None


def test_dispose_blocked_by_open_assignment(api_client, make_user, make_asset, disposal_reference):
    operator = _operator(make_user, disposal_reference)
    custodian = make_user("fr14-custodian", "employee")
    asset = make_asset("FR14-002")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json"
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "DISPOSAL_BLOCKED"
    assert "open_assignment" in error["field_errors"]["blockers"]


def test_dispose_force_override_requires_elevated_role(
    api_client, make_user, make_asset, disposal_reference
):
    operator = _operator(make_user, disposal_reference)
    custodian = make_user("fr14-custodian-2", "employee")
    asset = make_asset("FR14-003")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )
    # Operators cannot override BR-006 blockers.
    denied = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"force": True}, format="json"
    )
    assert denied.status_code == 409
    # Asset managers may force an authorized exception.
    manager = make_user("fr14-manager", "asset_manager")
    api_client.force_authenticate(manager)
    forced = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/",
        {"method": "write_off", "reason": "Authorized exception", "force": True},
        format="json",
    )
    assert forced.status_code == 200, forced.json()
    asset.refresh_from_db()
    assert asset.status.code == "disposed"
    assert asset.disposal_date is not None
    assert asset.disposal_method == "write_off"


def test_disposed_is_terminal(api_client, make_user, make_asset, disposal_reference):
    operator = _operator(make_user, disposal_reference)
    custodian = make_user("fr14-custodian-3", "employee")
    asset = make_asset("FR14-004")
    api_client.force_authenticate(operator)
    disposed = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json"
    )
    assert disposed.status_code == 200
    # Disposed assets are non-reusable: further transitions are rejected.
    assign = api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )
    assert assign.status_code == 409
    assert assign.json()["error"]["code"] == "STATUS_TRANSITION_INVALID"


def test_reopen_requires_admin_and_justification(
    api_client, make_user, make_asset, disposal_reference
):
    from apps.assets.models import LifecycleEvent

    operator = _operator(make_user, disposal_reference)
    asset = make_asset("FR14-005")
    api_client.force_authenticate(operator)
    api_client.post(f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json")

    # Operators cannot reopen.
    denied = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reopen/", {"justification": "Mistake"}, format="json"
    )
    assert denied.status_code == 403

    admin = make_user("fr14-admin", "system_admin")
    api_client.force_authenticate(admin)
    # Justification is mandatory.
    missing = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reopen/", {"justification": " "}, format="json"
    )
    assert missing.status_code == 400
    assert "justification" in missing.json()["error"]["field_errors"]

    reopened = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reopen/",
        {"justification": "Disposed in error during audit."},
        format="json",
    )
    assert reopened.status_code == 200
    asset.refresh_from_db()
    assert asset.status.code == "retired"
    # Disposal data is retained as history (BR-003).
    assert asset.disposal_date is not None
    assert LifecycleEvent.objects.filter(asset=asset, event_type="reopened").exists()


def test_reopen_rejects_non_disposed(api_client, make_user, make_asset, disposal_reference):
    admin = make_user("fr14-admin-2", "system_admin")
    asset = make_asset("FR14-006")
    api_client.force_authenticate(admin)
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reopen/", {"justification": "Why not"}, format="json"
    )
    assert response.status_code == 409


def test_dispose_idempotent_replay(api_client, make_user, make_asset, disposal_reference):
    operator = _operator(make_user, disposal_reference)
    asset = make_asset("FR14-007")
    api_client.force_authenticate(operator)
    payload = {"method": "recycle"}
    first = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="dispose-key-1",
    )
    assert first.status_code == 200
    replay = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="dispose-key-1",
    )
    # A real second attempt would 409 (terminal status).
    assert replay.status_code == 200
    assert replay.json() == first.json()


def test_disposed_assets_searchable_by_authorized_users(
    api_client, make_user, make_asset, disposal_reference
):
    operator = _operator(make_user, disposal_reference)
    asset = make_asset("FR14-008")
    api_client.force_authenticate(operator)
    api_client.post(f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json")
    manager = make_user("fr14-manager-2", "asset_manager")
    api_client.force_authenticate(manager)
    response = api_client.get("/api/v1/assets/", {"status_code": "disposed"})
    tags = [row["tag"] for row in response.json()["results"]]
    assert "FR14-008" in tags
