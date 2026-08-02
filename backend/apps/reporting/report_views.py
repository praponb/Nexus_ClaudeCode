"""Report catalog / detail / export endpoints (FR-021; design §11.3)."""

import csv
import io

from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit
from apps.core.csv_utils import sanitize_csv_value
from apps.reporting.reports import REPORTS, run_report

REPORT_ROLES = {"system_admin", "asset_manager", "department_manager", "auditor"}


class CanReadReports(BasePermission):
    message = "You do not have permission to view reports."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", "") in REPORT_ROLES)


class ReportCatalogView(APIView):
    """GET /reports/ — the 14 default reports (FR-021)."""

    permission_classes = [IsAuthenticated, CanReadReports]

    def get(self, request) -> Response:
        return Response(
            {
                "results": [
                    {
                        "type": report_type,
                        "name": report["name"],
                        "description": report["description"],
                        "params": report["params"],
                    }
                    for report_type, report in REPORTS.items()
                ]
            }
        )


class ReportDetailView(APIView):
    """GET /reports/:type/ — run a report with optional date filters."""

    permission_classes = [IsAuthenticated, CanReadReports]

    def get(self, request, report_type: str) -> Response:
        return Response(run_report(report_type, user=request.user, params=request.query_params))


class ReportExportView(APIView):
    """POST /reports/:type/export/ — CSV export of a report run (audited)."""

    permission_classes = [IsAuthenticated, CanReadReports]

    def post(self, request, report_type: str):
        from django.http import FileResponse

        params = request.data if isinstance(request.data, dict) else {}
        result = run_report(report_type, user=request.user, params=params)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(result["columns"])
        for row in result["rows"]:
            writer.writerow([sanitize_csv_value(value) for value in row])
        payload = buffer.getvalue().encode("utf-8-sig")
        record_audit(
            actor=request.user,
            action="report.export",
            after={"report": report_type, "row_count": len(result["rows"])},
            correlation_id=getattr(request, "correlation_id", None),
        )
        return FileResponse(
            io.BytesIO(payload),
            content_type="text/csv; charset=utf-8",
            as_attachment=True,
            filename=f"report-{report_type}.csv",
        )
