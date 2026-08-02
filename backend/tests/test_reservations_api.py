"""Reservation list endpoint (FR-010 completion; Rev 1.2 §11.3)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from datetime import timedelta  # noqa: E402

from django.utils import timezone  # noqa: E402

pytestmark = pytest.mark.django_db


def _make_reservation(asset, requester, **kwargs):
    from apps.assignments.models import Reservation

    now = timezone.now()
    defaults = {
        "asset": asset,
        "requester": requester,
        "start_at": now - timedelta(days=3),
        "end_at": now - timedelta(days=1),
        "status": "confirmed",
    }
    defaults.update(kwargs)
    return Reservation.objects.create(**defaults)


def test_reservations_list_scoped_and_filterable(api_client, make_user, make_asset, reference):
    operator = make_user("res-operator", "operator", scope_department=reference.department)
    outsider = make_user("res-outsider", "employee")
    visible = make_asset("RES-001")
    hidden = make_asset("RES-002", department=reference.other_department)
    _make_reservation(visible, operator)
    _make_reservation(hidden, outsider)

    api_client.force_authenticate(operator)
    response = api_client.get("/api/v1/reservations/")
    assert response.status_code == 200
    tags = [row["asset"]["tag"] for row in response.json()["results"]]
    assert tags == ["RES-001"]

    # Own requests are visible even when the asset is out of scope.
    _make_reservation(hidden, operator)
    response = api_client.get("/api/v1/reservations/")
    tags = sorted(row["asset"]["tag"] for row in response.json()["results"])
    assert tags == ["RES-001", "RES-002"]

    # Filters: asset + status.
    response = api_client.get(
        "/api/v1/reservations/", {"asset": str(visible.uuid), "status": "confirmed"}
    )
    tags = [row["asset"]["tag"] for row in response.json()["results"]]
    assert tags == ["RES-001"]


def test_reservations_overdue_filter(api_client, make_user, make_asset, reference):
    operator = make_user("res-operator-2", "operator", scope_department=reference.department)
    asset = make_asset("RES-010")
    now = timezone.now()
    _make_reservation(asset, operator)  # active, ended yesterday -> overdue
    _make_reservation(
        asset,
        operator,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=2),
    )  # future -> not overdue
    _make_reservation(asset, operator, status="returned")  # closed -> not overdue

    api_client.force_authenticate(operator)
    response = api_client.get("/api/v1/reservations/", {"overdue": "true"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["overdue"] is True
    assert results[0]["status"] == "confirmed"

    unfiltered = api_client.get("/api/v1/reservations/")
    assert len(unfiltered.json()["results"]) == 3
