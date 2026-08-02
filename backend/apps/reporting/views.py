from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assets.models import Asset, LifecycleEvent
from apps.assignments.models import Assignment, ExceptionReport
from apps.core import capabilities
from apps.core.exceptions import ApiException
from apps.core.permissions import scope_assets
from apps.reporting.models import SavedView
from apps.reporting.serializers import SavedViewSerializer


class SavedViewViewSet(viewsets.ModelViewSet):
    """Own saved views are fully manageable; shared views are readable by all (FR-006)."""

    serializer_class = SavedViewSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # drf-spectacular schema generation
            return SavedView.objects.none()
        user = self.request.user
        return SavedView.objects.filter(Q(owner=user) | Q(shared=True)).select_related("owner")

    def _clear_other_defaults(self, user, keep: SavedView) -> None:
        if keep.is_default:
            SavedView.objects.filter(owner=user, is_default=True).exclude(pk=keep.pk).update(
                is_default=False
            )

    def perform_create(self, serializer) -> None:
        view = serializer.save(owner=self.request.user)
        self._clear_other_defaults(self.request.user, view)

    def perform_update(self, serializer) -> None:
        view = self.get_object()
        if view.owner != self.request.user and not capabilities.is_system_admin(self.request.user):
            raise ApiException(
                403, "PERMISSION_DENIED", "Only the owner can modify this saved view."
            )
        saved = serializer.save()
        self._clear_other_defaults(self.request.user, saved)

    def perform_destroy(self, instance) -> None:
        if instance.owner != self.request.user and not capabilities.is_system_admin(
            self.request.user
        ):
            raise ApiException(
                403, "PERMISSION_DENIED", "Only the owner can delete this saved view."
            )
        instance.delete()


class DashboardSummaryView(APIView):
    """Scope-aware KPI aggregates (FR-020)."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        queryset = scope_assets(request.user, Asset.objects.all()).filter(record_status="active")
        now = timezone.now()
        today = now.date()
        by_status = [
            {"code": row["status__code"], "label": row["status__label"], "count": row["count"]}
            for row in queryset.values("status__code", "status__label")
            .annotate(count=Count("id"))
            .order_by("status__sort_order")
        ]
        by_category = [
            {"code": row["category__code"], "name": row["category__name"], "count": row["count"]}
            for row in queryset.values("category__code", "category__name")
            .annotate(count=Count("id"))
            .order_by("category__code")
        ]
        total = queryset.count()
        # Assets WITH an open assignment (LEFT JOIN null rows must not count).
        open_assignments = Assignment.objects.filter(returned_at__isnull=True)
        assigned = queryset.filter(id__in=open_assignments.values("asset_id")).count()
        overdue_returns = open_assignments.filter(
            expected_return_at__isnull=False,
            expected_return_at__lt=now,
            asset__in=queryset,
        ).count()
        recent_activity = [
            {
                "occurred_at": event.occurred_at,
                "event_type": event.event_type,
                "summary": event.summary,
                "asset": {"uuid": str(event.asset.uuid), "tag": event.asset.tag},
            }
            for event in LifecycleEvent.objects.filter(asset__in=queryset)
            .select_related("asset")
            .order_by("-occurred_at", "-id")[:10]
        ]
        payload = {
            "generated_at": now,
            "scope": "global" if capabilities.is_global_reader(request.user) else "restricted",
            "total_assets": total,
            "assigned": assigned,
            "unassigned": total - assigned,
            "missing_lost_stolen": queryset.filter(
                status__code__in=["missing", "lost", "stolen"]
            ).count(),
            "under_maintenance": queryset.filter(status__code="under_maintenance").count(),
            "overdue_returns": overdue_returns,
            "open_exceptions": ExceptionReport.objects.filter(
                status="open", asset__in=queryset
            ).count(),
            "warranty_expiring_30d": queryset.filter(
                warranty_end__gte=today, warranty_end__lte=today + timedelta(days=30)
            ).count(),
            "maintenance_due": queryset.filter(
                next_maintenance_due__isnull=False, next_maintenance_due__lte=today
            ).count(),
            "by_status": by_status,
            "by_category": by_category,
            "recent_activity": recent_activity,
        }
        return Response(payload)


class DataQualityIssuesView(APIView):
    """FR-028 v1: computed data-quality work queue (scoped). Issues are
    computed on read; resolution happens through the normal edit/workflow
    endpoints, preserving audit history."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        queryset = scope_assets(
            request.user,
            Asset.objects.select_related("status", "condition").filter(record_status="active"),
        )
        now = timezone.now()
        issues: list[dict] = []

        def add(issue_type: str, severity: str, asset: Asset, message: str) -> None:
            issues.append(
                {
                    "type": issue_type,
                    "severity": severity,
                    "asset": {"uuid": str(asset.uuid), "tag": asset.tag, "name": asset.name},
                    "message": message,
                }
            )

        for asset in queryset.filter(serial_number="")[:50]:
            add("missing_serial", "warning", asset, "No serial number recorded.")
        for asset in queryset.filter(condition__isnull=True)[:50]:
            add("missing_condition", "warning", asset, "No condition recorded.")
        for asset in queryset.filter(warranty_end__isnull=False, warranty_end__lt=now.date())[:50]:
            add("warranty_expired", "warning", asset, "Warranty has expired.")

        # Possible duplicates: same non-empty serial on multiple active assets.
        duplicate_serials = (
            queryset.exclude(serial_number="")
            .values("serial_number")
            .annotate(count=Count("id"))
            .filter(count__gt=1)[:50]
        )
        for row in duplicate_serials:
            for asset in queryset.filter(serial_number=row["serial_number"])[:5]:
                add(
                    "possible_duplicate_serial",
                    "error",
                    asset,
                    f"Serial '{row['serial_number']}' is shared by {row['count']} assets.",
                )

        # Expired assignments: open assignment past its expected return.
        expired = Assignment.objects.filter(
            returned_at__isnull=True,
            expected_return_at__isnull=False,
            expected_return_at__lt=now,
            asset__in=queryset,
        ).select_related("asset")[:50]
        for assignment in expired:
            add(
                "expired_assignment",
                "error",
                assignment.asset,
                "Assignment is past its expected return date.",
            )

        # Lifecycle inconsistency: status vs. actual assignment presence.
        open_assignment_asset_ids = Assignment.objects.filter(
            returned_at__isnull=True, asset__in=queryset
        ).values("asset_id")
        for asset in queryset.filter(status__code="assigned").exclude(
            id__in=open_assignment_asset_ids
        )[:50]:
            add(
                "status_assignment_mismatch",
                "error",
                asset,
                "Status is Assigned but no active assignment exists.",
            )

        severity_rank = {"error": 0, "warning": 1}
        issues.sort(key=lambda issue: (severity_rank.get(issue["severity"], 2), issue["type"]))
        return Response(
            {
                "generated_at": now,
                "total": len(issues),
                "issues": issues[:200],
            }
        )
