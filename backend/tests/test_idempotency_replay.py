"""Idempotency-Key replay coverage for transfer, return, and reserve
(D-08 residual from Cycle 2; QA Cycle-2 finding).

Each test proves the handler ran exactly once: a second *real* execution
would conflict (409), so a 2xx replay with an identical body demonstrates
the stored response was served without re-running the mutation.
"""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from datetime import timedelta  # noqa: E402

from django.utils import timezone  # noqa: E402

pytestmark = pytest.mark.django_db


def _operator(make_user, reference):
    return make_user("replay-operator", "operator", scope_department=reference.department)


def test_transfer_replay_runs_once(api_client, make_user, make_asset, workflow_reference):
    from apps.assignments.models import TransferRecord
    from apps.reference_data.models import Location

    operator = _operator(make_user, workflow_reference)
    destination = Location.objects.create(code="east", name="East Office")
    asset = make_asset("IDEM-T-1")
    api_client.force_authenticate(operator)
    payload = {"to_location": str(destination.uuid), "reason": "Site consolidation"}
    first = api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="transfer-key-1",
    )
    assert first.status_code == 200
    replay = api_client.post(
        f"/api/v1/assets/{asset.uuid}/transfer/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="transfer-key-1",
    )
    # A real second attempt would be 409 TRANSFER_IN_PROGRESS.
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert TransferRecord.objects.filter(asset=asset).count() == 1


def test_return_replay_runs_once(api_client, make_user, make_asset, workflow_reference):
    from apps.assignments.models import Assignment

    operator = _operator(make_user, workflow_reference)
    custodian = make_user("replay-custodian", "employee")
    asset = make_asset("IDEM-R-1")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )
    payload = {"close_reason": "returned"}
    first = api_client.post(
        f"/api/v1/assets/{asset.uuid}/return/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="return-key-1",
    )
    assert first.status_code == 200
    replay = api_client.post(
        f"/api/v1/assets/{asset.uuid}/return/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="return-key-1",
    )
    # A real second attempt would be 409 ASSIGNMENT_CONFLICT.
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assignment = Assignment.objects.get(asset=asset)
    assert assignment.returned_at is not None


def test_reserve_replay_runs_once(api_client, make_user, make_asset, workflow_reference):
    from apps.assignments.models import Reservation

    operator = _operator(make_user, workflow_reference)
    asset = make_asset("IDEM-V-1")
    api_client.force_authenticate(operator)
    now = timezone.now()
    payload = {
        "start_at": (now + timedelta(days=1)).isoformat(),
        "end_at": (now + timedelta(days=2)).isoformat(),
    }
    first = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reserve/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="reserve-key-1",
    )
    assert first.status_code == 201
    replay = api_client.post(
        f"/api/v1/assets/{asset.uuid}/reserve/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="reserve-key-1",
    )
    # A real second attempt would be 409 RESERVATION_CONFLICT.
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert Reservation.objects.filter(asset=asset).count() == 1
