"""Reports catalog, scoped execution, and CSV export (FR-021)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from datetime import timedelta  # noqa: E402

from django.utils import timezone  # noqa: E402

pytestmark = pytest.mark.django_db

EXPECTED_REPORT_TYPES = {
    "asset-register",
    "assets-by-status",
    "assets-by-category",
    "assets-by-location",
    "assets-by-department",
    "current-assignments",
    "overdue-returns",
    "assignment-history",
    "warranty-expiry",
    "maintenance-due",
    "maintenance-history",
    "exception-report",
    "stocktake-variance",
    "disposal-report",
}


def test_report_catalog_lists_14_reports(api_client, make_user):
    manager = make_user("rep-manager", "asset_manager")
    api_client.force_authenticate(manager)
    response = api_client.get("/api/v1/reports/")
    assert response.status_code == 200
    types = {row["type"] for row in response.json()["results"]}
    assert types == EXPECTED_REPORT_TYPES


def test_reports_require_report_role(api_client, make_user, reference):
    operator = make_user("rep-operator", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    assert api_client.get("/api/v1/reports/").status_code == 403
    assert api_client.get("/api/v1/reports/assets-by-status/").status_code == 403


def test_assets_by_status_totals_reconcile_with_scope(api_client, make_user, make_asset, reference):
    dept_manager = make_user(
        "rep-deptmgr", "department_manager", scope_department=reference.department
    )
    make_asset("REP-001")
    make_asset("REP-002", status=reference.assigned)
    make_asset("REP-003", department=reference.other_department)
    api_client.force_authenticate(dept_manager)

    response = api_client.get("/api/v1/reports/assets-by-status/")
    assert response.status_code == 200
    body = response.json()
    # Scoped: the other-department asset is excluded from every group.
    assert body["totals"]["total_assets"] == 2
    assert sum(row[1] for row in body["rows"]) == 2

    manager = make_user("rep-manager-2", "asset_manager")
    api_client.force_authenticate(manager)
    body = api_client.get("/api/v1/reports/assets-by-status/").json()
    assert body["totals"]["total_assets"] == 3


def test_warranty_expiry_report(api_client, make_user, make_asset, reference):
    manager = make_user("rep-manager-3", "asset_manager")
    today = timezone.now().date()
    make_asset("REP-010", warranty_end=today + timedelta(days=30))
    make_asset("REP-011", warranty_end=today + timedelta(days=200))
    api_client.force_authenticate(manager)
    response = api_client.get("/api/v1/reports/warranty-expiry/")
    body = response.json()
    tags = [row[0] for row in body["rows"]]
    assert tags == ["REP-010"]  # default 90-day window


def test_unknown_report_type_404(api_client, make_user):
    manager = make_user("rep-manager-4", "asset_manager")
    api_client.force_authenticate(manager)
    assert api_client.get("/api/v1/reports/not-a-report/").status_code == 404


def test_invalid_date_param_400(api_client, make_user):
    manager = make_user("rep-manager-5", "asset_manager")
    api_client.force_authenticate(manager)
    response = api_client.get("/api/v1/reports/assignment-history/", {"date_from": "06/01/2026"})
    assert response.status_code == 400
    assert "date_from" in response.json()["error"]["field_errors"]


def test_report_export_csv_audited(api_client, make_user, make_asset, reference):
    from apps.audit.models import AuditEvent

    manager = make_user("rep-manager-6", "asset_manager")
    make_asset("REP-020", name="=dangerous")
    api_client.force_authenticate(manager)
    response = api_client.post("/api/v1/reports/asset-register/export/", {}, format="json")
    assert response.status_code == 200
    content = b"".join(response.streaming_content).decode("utf-8-sig")
    assert "tag" in content.splitlines()[0]
    assert "'=dangerous" in content  # formula-injection mitigation
    assert AuditEvent.objects.filter(action="report.export").exists()


def test_auditor_can_run_reports(api_client, make_user, make_asset, reference):
    auditor = make_user("rep-auditor", "auditor")
    make_asset("REP-030")
    api_client.force_authenticate(auditor)
    response = api_client.get("/api/v1/reports/asset-register/")
    assert response.status_code == 200
    assert response.json()["totals"]["total_assets"] == 1
