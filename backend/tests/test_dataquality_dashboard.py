"""Mandatory Cycle-3 backend coverage (QA Cycle-2 findings):
FR-028 data-quality queue and FR-020 dashboard KPI completion (TC-FR-020-04).
"""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from datetime import timedelta  # noqa: E402

from django.utils import timezone  # noqa: E402

pytestmark = pytest.mark.django_db


def _operator(make_user, reference, username="dq-operator"):
    return make_user(username, "operator", scope_department=reference.department)


# -- FR-028 data-quality queue -----------------------------------------------


def test_data_quality_flags_missing_data(api_client, make_user, make_asset, reference):
    operator = _operator(make_user, reference)
    make_asset("DQ-001", serial_number="S-CLEAN")  # serial + condition present -> clean
    make_asset("DQ-002", serial_number="")
    make_asset("DQ-003", serial_number="S-3", condition=None)
    api_client.force_authenticate(operator)

    response = api_client.get("/api/v1/data-quality/issues/")
    assert response.status_code == 200
    body = response.json()
    by_type = {}
    for issue in body["issues"]:
        by_type.setdefault(issue["type"], []).append(issue)
    assert [row["asset"]["tag"] for row in by_type["missing_serial"]] == ["DQ-002"]
    assert [row["asset"]["tag"] for row in by_type["missing_condition"]] == ["DQ-003"]
    assert by_type["missing_serial"][0]["severity"] == "warning"
    assert body["total"] == len(body["issues"])


def test_data_quality_flags_duplicates_and_inconsistencies(
    api_client, make_user, make_asset, reference
):
    from apps.assignments.models import Assignment

    operator = _operator(make_user, reference)
    make_asset("DQ-010", serial_number="SHARED-1")
    make_asset("DQ-011", serial_number="SHARED-1")
    # Status says Assigned but no open assignment exists.
    make_asset("DQ-012", serial_number="S-12", status=reference.assigned)
    # Expired assignment (open, past expected return).
    stale = make_asset("DQ-013", serial_number="S-13")
    Assignment.objects.create(
        asset=stale,
        custodian=operator,
        expected_return_at=timezone.now() - timedelta(days=2),
    )
    stale.status = reference.assigned
    stale.save(update_fields=["status"])
    # Expired warranty.
    make_asset(
        "DQ-014",
        serial_number="S-14",
        warranty_start=timezone.now().date() - timedelta(days=400),
        warranty_end=timezone.now().date() - timedelta(days=10),
    )
    api_client.force_authenticate(operator)

    body = api_client.get("/api/v1/data-quality/issues/").json()
    by_type = {}
    for issue in body["issues"]:
        by_type.setdefault(issue["type"], []).append(issue)

    duplicate_tags = sorted(row["asset"]["tag"] for row in by_type["possible_duplicate_serial"])
    assert duplicate_tags == ["DQ-010", "DQ-011"]
    assert by_type["possible_duplicate_serial"][0]["severity"] == "error"

    assert [row["asset"]["tag"] for row in by_type["status_assignment_mismatch"]] == ["DQ-012"]
    assert [row["asset"]["tag"] for row in by_type["expired_assignment"]] == ["DQ-013"]
    assert [row["asset"]["tag"] for row in by_type["warranty_expired"]] == ["DQ-014"]

    # Errors sort before warnings in the queue.
    severities = [issue["severity"] for issue in body["issues"]]
    assert severities == sorted(severities, key=lambda s: 0 if s == "error" else 1)


def test_data_quality_queue_is_scoped(api_client, make_user, make_asset, reference):
    operator = _operator(make_user, reference)
    make_asset("DQ-020", serial_number="S-20", condition=None)
    make_asset(
        "DQ-021", serial_number="S-21", condition=None, department=reference.other_department
    )
    api_client.force_authenticate(operator)
    body = api_client.get("/api/v1/data-quality/issues/").json()
    tags = [issue["asset"]["tag"] for issue in body["issues"]]
    assert "DQ-020" in tags
    assert "DQ-021" not in tags


# -- FR-020 dashboard KPI completion (TC-FR-020-04) ---------------------------


def test_dashboard_full_kpi_set(api_client, make_user, make_asset, workflow_reference):
    from apps.assignments.models import Assignment, ExceptionReport

    ref = workflow_reference
    operator = _operator(make_user, ref, "dash-operator")
    today = timezone.now().date()

    assigned_asset = make_asset("KPI-001", serial_number="K-1", status=ref.assigned)
    Assignment.objects.create(
        asset=assigned_asset,
        custodian=operator,
        expected_return_at=timezone.now() - timedelta(days=1),  # overdue
    )
    ExceptionReport.objects.create(asset=assigned_asset, report_type="damaged", reporter=operator)
    make_asset("KPI-002", serial_number="K-2", status=ref.statuses["under_maintenance"])
    make_asset("KPI-003", serial_number="K-3", warranty_end=today + timedelta(days=10))
    make_asset("KPI-004", serial_number="K-4", next_maintenance_due=today - timedelta(days=1))
    make_asset("KPI-005", serial_number="K-5", status=ref.statuses["missing"])

    api_client.force_authenticate(operator)
    response = api_client.get("/api/v1/dashboard/summary/")
    assert response.status_code == 200
    body = response.json()

    assert body["total_assets"] == 5
    assert body["assigned"] == 1
    assert body["unassigned"] == 4
    assert body["overdue_returns"] == 1
    assert body["under_maintenance"] == 1
    assert body["warranty_expiring_30d"] == 1
    assert body["maintenance_due"] == 1
    assert body["missing_lost_stolen"] == 1
    assert body["open_exceptions"] == 1
    assert body["scope"] == "restricted"
    assert body["generated_at"]
    status_codes = {row["code"] for row in body["by_status"]}
    assert {"assigned", "under_maintenance", "missing", "in_stock"} <= status_codes
    assert any(row["code"] == "laptop" for row in body["by_category"])
    assert isinstance(body["recent_activity"], list)


def test_dashboard_scope_totals_are_not_misleading(api_client, make_user, make_asset, reference):
    operator = _operator(make_user, reference, "dash-scoped")
    make_asset("KPI-100", serial_number="K-100")
    make_asset("KPI-101", serial_number="K-101", department=reference.other_department)
    api_client.force_authenticate(operator)
    body = api_client.get("/api/v1/dashboard/summary/").json()
    assert body["total_assets"] == 1
    assert body["scope"] == "restricted"

    manager = make_user("dash-manager", "asset_manager")
    api_client.force_authenticate(manager)
    body = api_client.get("/api/v1/dashboard/summary/").json()
    assert body["total_assets"] == 2
    assert body["scope"] == "global"
