"""Default report catalog (FR-021).

Every report is permission-scoped (scope_assets) so totals always reconcile
with the record set the requesting user is permitted to see. Finance columns
are emitted only for roles with finance.view. Date params are ISO YYYY-MM-DD.
"""

from datetime import timedelta

from django.utils import timezone

from apps.assets.models import Asset
from apps.assignments.models import Assignment, ExceptionReport
from apps.core import capabilities
from apps.core.exceptions import ApiException
from apps.core.permissions import scope_assets
from apps.maintenance.models import MaintenanceRecord
from apps.stocktakes.models import StocktakeSession

MAX_ROWS = 500


def parse_date(raw, field: str):
    if raw in (None, ""):
        return None
    try:
        from datetime import datetime

        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            f"Parameter '{field}' must be a YYYY-MM-DD date.",
            field_errors={field: ["Expected YYYY-MM-DD."]},
        ) from None


def _scoped_assets(user):
    return scope_assets(
        user,
        Asset.objects.select_related(
            "status", "condition", "category", "department", "location", "custodian"
        ).filter(record_status="active"),
    )


def _asset_brief(asset) -> list:
    return [
        asset.tag,
        asset.name,
        asset.status.label if asset.status else "",
        asset.category.name if asset.category else "",
        asset.department.name if asset.department else "",
        asset.location.name if asset.location else "",
    ]


def _count_report(user, field: str, label_field: str) -> dict:
    from django.db.models import Count

    rows = []
    grouped = (
        _scoped_assets(user)
        .values(field, label_field)
        .annotate(count=Count("id"))
        .order_by(label_field)
    )
    total = 0
    for row in grouped:
        label = row[label_field] or "(none)"
        rows.append([label, row["count"]])
        total += row["count"]
    return {
        "columns": ["group", "count"],
        "rows": rows,
        "totals": {"total_assets": total},
    }


def _asset_register(user, params) -> dict:
    include_finance = capabilities.can_view_finance(user)
    columns = ["tag", "name", "status", "category", "department", "location", "custodian"]
    if include_finance:
        columns += ["purchase_amount", "purchase_currency"]
    rows = []
    for asset in _scoped_assets(user).order_by("tag")[:MAX_ROWS]:
        row = _asset_brief(asset) + [str(asset.custodian) if asset.custodian else ""]
        if include_finance:
            row += [
                f"{asset.purchase_price:.2f}" if asset.purchase_price is not None else "",
                asset.purchase_currency,
            ]
        rows.append(row)
    return {"columns": columns, "rows": rows, "totals": {"total_assets": len(rows)}}


def _assignments(user, params, *, overdue_only: bool, history: bool) -> dict:
    visible = _scoped_assets(user)
    queryset = Assignment.objects.filter(asset__in=visible).select_related(
        "asset", "custodian", "department", "location"
    )
    now = timezone.now()
    if overdue_only:
        queryset = queryset.filter(
            returned_at__isnull=True,
            expected_return_at__isnull=False,
            expected_return_at__lt=now,
        )
    elif history:
        date_from = parse_date(params.get("date_from"), "date_from")
        date_to = parse_date(params.get("date_to"), "date_to")
        queryset = queryset.filter(returned_at__isnull=False)
        if date_from:
            queryset = queryset.filter(returned_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(returned_at__date__lte=date_to)
    else:
        queryset = queryset.filter(returned_at__isnull=True)
    rows = [
        [
            assignment.asset.tag,
            assignment.asset.name,
            str(assignment.custodian) if assignment.custodian else "",
            assignment.assigned_at.date().isoformat(),
            (
                assignment.expected_return_at.date().isoformat()
                if assignment.expected_return_at
                else ""
            ),
            (assignment.returned_at.date().isoformat() if assignment.returned_at else ""),
        ]
        for assignment in queryset.order_by("-assigned_at")[:MAX_ROWS]
    ]
    return {
        "columns": ["tag", "name", "custodian", "assigned", "expected_return", "returned"],
        "rows": rows,
        "totals": {"count": len(rows)},
    }


def _current_assignments(user, params) -> dict:
    return _assignments(user, params, overdue_only=False, history=False)


def _overdue_returns(user, params) -> dict:
    return _assignments(user, params, overdue_only=True, history=False)


def _assignment_history(user, params) -> dict:
    return _assignments(user, params, overdue_only=False, history=True)


def _warranty_expiry(user, params) -> dict:
    today = timezone.now().date()
    date_from = parse_date(params.get("date_from"), "date_from") or today
    date_to = parse_date(params.get("date_to"), "date_to") or (today + timedelta(days=90))
    queryset = _scoped_assets(user).filter(
        warranty_end__isnull=False, warranty_end__gte=date_from, warranty_end__lte=date_to
    )
    rows = [
        _asset_brief(asset) + [asset.warranty_end.isoformat()]
        for asset in queryset.order_by("warranty_end")[:MAX_ROWS]
    ]
    return {
        "columns": ["tag", "name", "status", "category", "department", "location", "warranty_end"],
        "rows": rows,
        "totals": {"count": len(rows)},
    }


def _maintenance_due(user, params) -> dict:
    today = timezone.now().date()
    queryset = _scoped_assets(user).filter(
        next_maintenance_due__isnull=False, next_maintenance_due__lte=today
    )
    rows = [
        _asset_brief(asset) + [asset.next_maintenance_due.isoformat()]
        for asset in queryset.order_by("next_maintenance_due")[:MAX_ROWS]
    ]
    return {
        "columns": [
            "tag",
            "name",
            "status",
            "category",
            "department",
            "location",
            "next_maintenance_due",
        ],
        "rows": rows,
        "totals": {"count": len(rows)},
    }


def _maintenance_history(user, params) -> dict:
    visible = _scoped_assets(user)
    queryset = MaintenanceRecord.objects.filter(asset__in=visible).select_related(
        "asset", "maintenance_type"
    )
    date_from = parse_date(params.get("date_from"), "date_from")
    date_to = parse_date(params.get("date_to"), "date_to")
    if date_from:
        queryset = queryset.filter(started_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(started_at__date__lte=date_to)
    include_finance = capabilities.can_view_finance(user)
    columns = ["tag", "type", "issue", "provider", "started", "completed", "status"]
    if include_finance:
        columns += ["cost", "currency"]
    rows = []
    for record in queryset.order_by("-started_at")[:MAX_ROWS]:
        row = [
            record.asset.tag,
            record.maintenance_type.name,
            record.issue[:80],
            record.provider,
            record.started_at.date().isoformat(),
            (record.completed_at.date().isoformat() if record.completed_at else ""),
            record.status,
        ]
        if include_finance:
            row += [
                f"{record.cost:.2f}" if record.cost is not None else "",
                record.cost_currency,
            ]
        rows.append(row)
    return {"columns": columns, "rows": rows, "totals": {"count": len(rows)}}


def _exception_report(user, params) -> dict:
    visible = _scoped_assets(user)
    queryset = ExceptionReport.objects.filter(asset__in=visible).select_related("asset", "reporter")
    if params.get("status"):
        queryset = queryset.filter(status=params["status"])
    rows = [
        [
            report.asset.tag,
            report.report_type,
            report.status,
            str(report.reporter) if report.reporter else "",
            report.created_at.date().isoformat(),
            report.resolution[:80],
        ]
        for report in queryset.order_by("-created_at")[:MAX_ROWS]
    ]
    return {
        "columns": ["tag", "type", "status", "reporter", "reported", "resolution"],
        "rows": rows,
        "totals": {"count": len(rows)},
    }


def _stocktake_variance(user, params) -> dict:
    sessions = StocktakeSession.objects.filter(status=StocktakeSession.Status.CLOSED)
    from apps.stocktakes.services import compute_variance

    rows = []
    for session in sessions.order_by("-updated_at")[:50]:
        variance = compute_variance(session)
        rows.append(
            [
                session.name,
                variance["expected_count"],
                variance["found_count"],
                len(variance["not_found"]),
                len(variance["unexpected"]),
                len(variance["moved"]),
                len(variance["condition_mismatches"]),
            ]
        )
    return {
        "columns": [
            "session",
            "expected",
            "found",
            "not_found",
            "unexpected",
            "moved",
            "condition_mismatch",
        ],
        "rows": rows,
        "totals": {"sessions": len(rows)},
    }


def _disposal_report(user, params) -> dict:
    queryset = _scoped_assets(user).filter(status__code__in=["retired", "disposed"])
    date_from = parse_date(params.get("date_from"), "date_from")
    date_to = parse_date(params.get("date_to"), "date_to")
    if date_from:
        queryset = queryset.filter(disposal_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(disposal_date__lte=date_to)
    rows = [
        _asset_brief(asset)
        + [
            asset.retirement_date.isoformat() if asset.retirement_date else "",
            asset.disposal_date.isoformat() if asset.disposal_date else "",
            asset.disposal_method,
        ]
        for asset in queryset.order_by("-disposal_date", "tag")[:MAX_ROWS]
    ]
    return {
        "columns": [
            "tag",
            "name",
            "status",
            "category",
            "department",
            "location",
            "retirement_date",
            "disposal_date",
            "disposal_method",
        ],
        "rows": rows,
        "totals": {"count": len(rows)},
    }


REPORTS = {
    "asset-register": {
        "name": "Asset register",
        "description": "All permitted assets with identity and placement fields.",
        "params": [],
        "handler": _asset_register,
    },
    "assets-by-status": {
        "name": "Assets by status",
        "description": "Asset counts grouped by lifecycle status.",
        "params": [],
        "handler": lambda user, params: _count_report(user, "status__code", "status__label"),
    },
    "assets-by-category": {
        "name": "Assets by category",
        "description": "Asset counts grouped by category.",
        "params": [],
        "handler": lambda user, params: _count_report(user, "category__code", "category__name"),
    },
    "assets-by-location": {
        "name": "Assets by location",
        "description": "Asset counts grouped by location.",
        "params": [],
        "handler": lambda user, params: _count_report(user, "location__code", "location__name"),
    },
    "assets-by-department": {
        "name": "Assets by department",
        "description": "Asset counts grouped by owning department.",
        "params": [],
        "handler": lambda user, params: _count_report(user, "department__code", "department__name"),
    },
    "current-assignments": {
        "name": "Current assignments",
        "description": "Open assignments with custodian and expected return.",
        "params": [],
        "handler": _current_assignments,
    },
    "overdue-returns": {
        "name": "Overdue returns",
        "description": "Open assignments past their expected return date.",
        "params": [],
        "handler": _overdue_returns,
    },
    "assignment-history": {
        "name": "Assignment history",
        "description": "Closed assignments within an optional date range.",
        "params": ["date_from", "date_to"],
        "handler": _assignment_history,
    },
    "warranty-expiry": {
        "name": "Warranty expiry",
        "description": "Assets with warranties ending in the window (default: next 90 days).",
        "params": ["date_from", "date_to"],
        "handler": _warranty_expiry,
    },
    "maintenance-due": {
        "name": "Maintenance due",
        "description": "Assets whose next maintenance date has passed.",
        "params": [],
        "handler": _maintenance_due,
    },
    "maintenance-history": {
        "name": "Maintenance history",
        "description": "Maintenance/repair records in an optional date range (cost restricted).",
        "params": ["date_from", "date_to"],
        "handler": _maintenance_history,
    },
    "exception-report": {
        "name": "Lost/stolen/missing/damaged report",
        "description": "Exception reports with status and resolution.",
        "params": ["status"],
        "handler": _exception_report,
    },
    "stocktake-variance": {
        "name": "Stocktake variance",
        "description": "Final variance summary per closed stocktake session.",
        "params": [],
        "handler": _stocktake_variance,
    },
    "disposal-report": {
        "name": "Retirement and disposal",
        "description": "Retired and disposed assets in an optional date range.",
        "params": ["date_from", "date_to"],
        "handler": _disposal_report,
    },
}


def get_report(report_type: str) -> dict:
    report = REPORTS.get(report_type)
    if report is None:
        raise ApiException(404, "NOT_FOUND", "The requested resource was not found.")
    return report


def run_report(report_type: str, *, user, params: dict) -> dict:
    report = get_report(report_type)
    result = report["handler"](user, params)
    truncated = len(result["rows"]) >= MAX_ROWS
    return {
        "type": report_type,
        "name": report["name"],
        "generated_at": timezone.now(),
        "columns": result["columns"],
        "rows": result["rows"],
        "totals": result["totals"],
        "truncated": truncated,
    }
