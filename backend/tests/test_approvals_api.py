"""Approval workflows (FR-024): held actions, decisions, separation of
duties, immutable history, notifications."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _require_approval(reference, from_code: str, to_code: str):
    """Make the given transition require approval."""
    from apps.reference_data.models import AssetStatus, StatusTransitionRule

    from_status = AssetStatus.objects.get(code=from_code)
    to_status = AssetStatus.objects.get(code=to_code)
    rule = StatusTransitionRule.objects.get(from_status=from_status, to_status=to_status)
    rule.requires_approval = True
    rule.save(update_fields=["requires_approval"])
    return rule


def test_disposal_held_and_approved(api_client, make_user, make_asset, disposal_reference):
    from apps.approvals.models import ApprovalRequest
    from apps.notifications.models import Notification

    _require_approval(disposal_reference, "in_stock", "disposed")
    operator = make_user("ap-operator", "operator", scope_department=disposal_reference.department)
    manager = make_user("ap-manager", "asset_manager")
    asset = make_asset("AP-001")
    api_client.force_authenticate(operator)

    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/",
        {"method": "recycle", "reason": "End of life"},
        format="json",
    )
    assert response.status_code == 202, response.json()
    approval_uuid = response.json()["approval"]["uuid"]
    # Nothing mutated yet: the asset is untouched while pending.
    asset.refresh_from_db()
    assert asset.status.code == "in_stock"
    request = ApprovalRequest.objects.get(uuid=approval_uuid)
    assert request.status == "pending"
    assert request.request_type == "disposal"
    # Approvers were notified.
    assert Notification.objects.filter(recipient=manager, type="approval.requested").exists()

    # The requester cannot decide their own request (separation of duties).
    api_client.force_authenticate(operator)
    sod = api_client.post(f"/api/v1/approvals/{approval_uuid}/approve/", {}, format="json")
    assert sod.status_code == 403  # operator is not an approver role at all

    # A manager approves; the held disposal executes.
    api_client.force_authenticate(manager)
    approved = api_client.post(
        f"/api/v1/approvals/{approval_uuid}/approve/",
        {"comments": "Verified."},
        format="json",
    )
    assert approved.status_code == 200, approved.json()
    assert approved.json()["status"] == "approved"
    asset.refresh_from_db()
    assert asset.status.code == "disposed"
    # The requester received the mandatory decision notification.
    assert Notification.objects.filter(recipient=operator, type="approval.decided").exists()


def test_manager_separation_of_duties(api_client, make_user, make_asset, disposal_reference):
    _require_approval(disposal_reference, "in_stock", "disposed")
    requester = make_user("ap-mgr-req", "asset_manager")
    approver = make_user("ap-mgr-ok", "asset_manager")
    asset = make_asset("AP-002")
    api_client.force_authenticate(requester)
    created = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json"
    )
    approval_uuid = created.json()["approval"]["uuid"]

    own = api_client.post(f"/api/v1/approvals/{approval_uuid}/approve/", {}, format="json")
    assert own.status_code == 409
    assert own.json()["error"]["code"] == "SEPARATION_OF_DUTIES"

    api_client.force_authenticate(approver)
    approved = api_client.post(f"/api/v1/approvals/{approval_uuid}/approve/", {}, format="json")
    assert approved.status_code == 200


def test_reject_leaves_asset_unchanged(api_client, make_user, make_asset, disposal_reference):
    _require_approval(disposal_reference, "in_stock", "disposed")
    operator = make_user("ap-op-3", "operator", scope_department=disposal_reference.department)
    manager = make_user("ap-mgr-3", "asset_manager")
    asset = make_asset("AP-003")
    api_client.force_authenticate(operator)
    created = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json"
    )
    approval_uuid = created.json()["approval"]["uuid"]

    api_client.force_authenticate(manager)
    rejected = api_client.post(
        f"/api/v1/approvals/{approval_uuid}/reject/",
        {"comments": "Missing paperwork."},
        format="json",
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    asset.refresh_from_db()
    assert asset.status.code == "in_stock"

    # Decisions are immutable.
    again = api_client.post(f"/api/v1/approvals/{approval_uuid}/approve/", {}, format="json")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "APPROVAL_ALREADY_DECIDED"


def test_transfer_held_for_approval(api_client, make_user, make_asset, workflow_reference):
    from apps.assignments.models import TransferRecord
    from apps.reference_data.models import Location

    _require_approval(workflow_reference, "in_stock", "in_transit")
    operator = make_user("ap-op-4", "operator", scope_department=workflow_reference.department)
    manager = make_user("ap-mgr-4", "asset_manager")
    destination = Location.objects.create(code="west", name="West Office")
    asset = make_asset("AP-004")
    api_client.force_authenticate(operator)

    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/",
        {"to_location": str(destination.uuid), "reason": "Consolidation"},
        format="json",
    )
    assert response.status_code == 202
    approval_uuid = response.json()["approval"]["uuid"]
    assert not TransferRecord.objects.filter(asset=asset).exists()

    api_client.force_authenticate(manager)
    approved = api_client.post(f"/api/v1/approvals/{approval_uuid}/approve/", {}, format="json")
    assert approved.status_code == 200
    transfer = TransferRecord.objects.get(asset=asset)
    assert transfer.status == "in_transit"
    asset.refresh_from_db()
    assert asset.status.code == "in_transit"


def test_approval_inbox_scoping(api_client, make_user, make_asset, disposal_reference):
    _require_approval(disposal_reference, "in_stock", "disposed")
    operator = make_user("ap-op-5", "operator", scope_department=disposal_reference.department)
    manager = make_user("ap-mgr-5", "asset_manager")
    asset = make_asset("AP-005")
    api_client.force_authenticate(operator)
    created = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json"
    )
    approval_uuid = created.json()["approval"]["uuid"]

    # Requester sees their own request; manager sees pending inbox.
    own = api_client.get("/api/v1/approvals/", {"status": "pending"})
    assert [row["uuid"] for row in own.json()["results"]] == [approval_uuid]
    api_client.force_authenticate(manager)
    inbox = api_client.get("/api/v1/approvals/", {"status": "pending"})
    assert approval_uuid in [row["uuid"] for row in inbox.json()["results"]]


def test_no_approval_when_rule_does_not_require(
    api_client, make_user, make_asset, disposal_reference
):
    from apps.approvals.models import ApprovalRequest

    operator = make_user("ap-op-6", "operator", scope_department=disposal_reference.department)
    asset = make_asset("AP-006")
    api_client.force_authenticate(operator)
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json"
    )
    assert response.status_code == 200
    assert not ApprovalRequest.objects.filter(asset=asset).exists()


def test_approvals_disabled_config(api_client, make_user, make_asset, disposal_reference, settings):
    from apps.approvals.models import ApprovalRequest

    _require_approval(disposal_reference, "in_stock", "disposed")
    settings.APPROVALS_ENABLED = False
    operator = make_user("ap-op-7", "operator", scope_department=disposal_reference.department)
    asset = make_asset("AP-007")
    api_client.force_authenticate(operator)
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/dispose/", {"method": "recycle"}, format="json"
    )
    assert response.status_code == 200
    assert not ApprovalRequest.objects.filter(asset=asset).exists()
