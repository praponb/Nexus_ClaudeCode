"""Cycle-2 lifecycle workflow endpoints: assignment, return, transfer,
reservation/checkout, exception reports (FR-007…FR-010, FR-013), plus
Idempotency-Key semantics on create/transition endpoints (D-08, ADR-004).
"""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from datetime import timedelta  # noqa: E402

from django.utils import timezone  # noqa: E402

pytestmark = pytest.mark.django_db


def _operator(make_user, reference):
    return make_user("wf-operator", "operator", scope_department=reference.department)


def test_assign_closes_previous_and_sets_custodian(
    api_client, make_user, make_asset, workflow_reference
):
    from apps.assignments.models import Assignment

    operator = _operator(make_user, workflow_reference)
    custodian_a = make_user("custodian-a", "employee")
    custodian_b = make_user("custodian-b", "employee")
    asset = make_asset("WF-001")
    api_client.force_authenticate(operator)

    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian_a.uuid)}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["asset"]["status"]["code"] == "assigned"

    # Reassignment atomically closes the prior active assignment (BR-002).
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian_b.uuid)}, format="json"
    )
    assert response.status_code == 200
    assignments = Assignment.objects.filter(asset=asset)
    assert assignments.filter(returned_at__isnull=True).count() == 1
    assert assignments.filter(returned_at__isnull=False).count() == 1
    asset.refresh_from_db()
    assert asset.custodian == custodian_b


def test_assign_requires_destination(api_client, make_user, make_asset, workflow_reference):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("WF-002")
    api_client.force_authenticate(operator)
    response = api_client.post(f"/api/v1/assets/{asset.uuid}/assign/", {}, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_employee_cannot_assign(api_client, make_user, make_asset, workflow_reference):
    employee = make_user("wf-employee", "employee")
    asset = make_asset("WF-003", custodian=employee)
    api_client.force_authenticate(employee)
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(employee.uuid)}, format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_return_closes_assignment_and_marks_available(
    api_client, make_user, make_asset, workflow_reference
):
    operator = _operator(make_user, workflow_reference)
    custodian = make_user("custodian-c", "employee")
    asset = make_asset("WF-004")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/return/",
        {"condition": str(workflow_reference.condition.uuid), "notes": "All good."},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["asset"]["status"]["code"] == "available"
    assert body["assignment"]["status"] == "closed"
    asset.refresh_from_db()
    assert asset.custodian is None


def test_return_without_active_assignment_conflicts(
    api_client, make_user, make_asset, workflow_reference
):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("WF-005")
    api_client.force_authenticate(operator)
    response = api_client.post(f"/api/v1/assets/{asset.uuid}/return/", {}, format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ASSIGNMENT_CONFLICT"


def test_transfer_and_confirm_moves_location(api_client, make_user, make_asset, workflow_reference):
    from apps.reference_data.models import Location

    operator = _operator(make_user, workflow_reference)
    destination = Location.objects.create(code="wh", name="Warehouse")
    asset = make_asset("WF-006")
    api_client.force_authenticate(operator)

    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/",
        {"to_location": str(destination.uuid), "reason": "Office move"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["transfer"]["status"] == "in_transit"
    assert response.json()["asset"]["status"]["code"] == "in_transit"

    # A second transfer while one is open conflicts.
    conflict = api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/",
        {"to_location": str(destination.uuid)},
        format="json",
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "TRANSFER_IN_PROGRESS"

    # Recipient confirmation applies the destination (FR-008).
    confirmed = api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/", {"confirm": True}, format="json"
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["transfer"]["status"] == "received"
    asset.refresh_from_db()
    assert asset.location == destination
    assert asset.status.code == "available"


def test_transfer_with_custodian_confirm_creates_assignment(
    api_client, make_user, make_asset, workflow_reference
):
    from apps.assignments.models import Assignment

    operator = _operator(make_user, workflow_reference)
    recipient = make_user("recipient", "employee")
    asset = make_asset("WF-007")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/",
        {"to_custodian": str(recipient.uuid)},
        format="json",
    )
    confirmed = api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/", {"confirm": True}, format="json"
    )
    assert confirmed.status_code == 200
    asset.refresh_from_db()
    assert asset.custodian == recipient
    assert asset.status.code == "assigned"
    assert Assignment.objects.filter(asset=asset, returned_at__isnull=True).count() == 1


def test_reservation_overlap_conflict(api_client, make_user, make_asset, workflow_reference):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("WF-008")
    api_client.force_authenticate(operator)
    now = timezone.now()
    payload = {
        "start_at": (now + timedelta(days=1)).isoformat(),
        "end_at": (now + timedelta(days=3)).isoformat(),
        "purpose": "Demo",
    }
    response = api_client.post(f"/api/v1/assets/{asset.uuid}/reserve/", payload, format="json")
    assert response.status_code == 201
    overlap = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reserve/",
        {
            "start_at": (now + timedelta(days=2)).isoformat(),
            "end_at": (now + timedelta(days=4)).isoformat(),
        },
        format="json",
    )
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "RESERVATION_CONFLICT"


def test_checkout_reservation_creates_assignment(
    api_client, make_user, make_asset, workflow_reference
):
    from apps.assignments.models import Assignment, Reservation

    operator = _operator(make_user, workflow_reference)
    asset = make_asset("WF-009")
    api_client.force_authenticate(operator)
    now = timezone.now()
    reserved = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reserve/",
        {
            "start_at": (now + timedelta(hours=1)).isoformat(),
            "end_at": (now + timedelta(days=2)).isoformat(),
        },
        format="json",
    )
    reservation_uuid = reserved.json()["reservation"]["uuid"]
    checked_out = api_client.post(
        f"/api/v1/assets/{asset.uuid}/checkout/",
        {"reservation": reservation_uuid},
        format="json",
    )
    assert checked_out.status_code == 200
    reservation = Reservation.objects.get(uuid=reservation_uuid)
    assert reservation.status == "checked_out"
    assignment = Assignment.objects.get(asset=asset, returned_at__isnull=True)
    assert assignment.custodian == operator
    # Checking out the same reservation twice conflicts.
    bogus = api_client.post(
        f"/api/v1/assets/{asset.uuid}/checkout/",
        {"reservation": reservation_uuid},
        format="json",
    )
    assert bogus.status_code == 409


def test_report_exception_lost_and_resolve_preserves_history(
    api_client, make_user, make_asset, workflow_reference
):
    from apps.assignments.models import ExceptionReport

    operator = _operator(make_user, workflow_reference)
    asset = make_asset("WF-010")
    api_client.force_authenticate(operator)
    reported = api_client.post(
        f"/api/v1/assets/{asset.uuid}/report-exception/",
        {"report_type": "lost", "description": "Not found during audit."},
        format="json",
    )
    assert reported.status_code == 200
    assert reported.json()["asset"]["status"]["code"] == "lost"

    resolved = api_client.post(
        f"/api/v1/assets/{asset.uuid}/report-exception/",
        {"resolve": True, "resolution": "Located in storage room B."},
        format="json",
    )
    assert resolved.status_code == 200
    asset.refresh_from_db()
    assert asset.status.code == "available"
    # BR-003: the original report is preserved, not erased.
    report = ExceptionReport.objects.get(asset=asset)
    assert report.status == "resolved"
    assert report.report_type == "lost"
    assert "Located" in report.resolution


def test_report_damaged_sets_condition(api_client, make_user, make_asset, workflow_reference):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("WF-011")
    api_client.force_authenticate(operator)
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/report-exception/",
        {"report_type": "damaged", "description": "Cracked screen."},
        format="json",
    )
    assert response.status_code == 200
    asset.refresh_from_db()
    assert asset.condition.code == "damaged"


def test_employee_reports_own_asset(api_client, make_user, make_asset, workflow_reference):
    employee = make_user("reporter", "employee")
    asset = make_asset("WF-012", custodian=employee)
    api_client.force_authenticate(employee)
    response = api_client.post(
        f"/api/v1/assets/{asset.uuid}/report-exception/",
        {"report_type": "stolen", "description": "Stolen from my desk."},
        format="json",
    )
    assert response.status_code == 200
    asset.refresh_from_db()
    assert asset.status.code == "stolen"


def test_idempotency_key_replays_assign(api_client, make_user, make_asset, workflow_reference):
    from apps.assignments.models import Assignment

    operator = _operator(make_user, workflow_reference)
    custodian = make_user("idem-custodian", "employee")
    asset = make_asset("WF-013")
    api_client.force_authenticate(operator)
    payload = {"custodian": str(custodian.uuid)}
    first = api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="assign-key-1",
    )
    assert first.status_code == 200
    replay = api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="assign-key-1",
    )
    assert replay.status_code == 200
    assert replay.json() == first.json()
    # The handler ran once: exactly one assignment exists.
    assert Assignment.objects.filter(asset=asset).count() == 1


def test_idempotency_key_reuse_with_different_payload_conflicts(
    api_client, make_user, make_asset, workflow_reference
):
    operator = _operator(make_user, workflow_reference)
    asset = make_asset("WF-014")
    other = make_user("idem-other", "employee")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/",
        {"custodian": str(other.uuid)},
        format="json",
        HTTP_IDEMPOTENCY_KEY="assign-key-2",
    )
    conflict = api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/",
        {"notes": "different payload"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="assign-key-2",
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_idempotent_asset_create(api_client, make_user, workflow_reference):
    from apps.assets.models import Asset

    operator = _operator(make_user, workflow_reference)
    api_client.force_authenticate(operator)
    payload = {
        "name": "Idempotent laptop",
        "category": str(workflow_reference.category.uuid),
        "status": str(workflow_reference.in_stock.uuid),
        "condition": str(workflow_reference.condition.uuid),
        "department": str(workflow_reference.department.uuid),
        "location": str(workflow_reference.location.uuid),
        "acquisition_type": "purchased",
    }
    first = api_client.post(
        "/api/v1/assets/", payload, format="json", HTTP_IDEMPOTENCY_KEY="create-key-1"
    )
    assert first.status_code == 201, first.json()
    replay = api_client.post(
        "/api/v1/assets/", payload, format="json", HTTP_IDEMPOTENCY_KEY="create-key-1"
    )
    assert replay.status_code == 201
    assert replay.json()["asset"]["uuid"] == first.json()["asset"]["uuid"]
    assert Asset.objects.filter(name="Idempotent laptop").count() == 1
