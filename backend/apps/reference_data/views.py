"""Reference-data endpoints (FR-026).

Reads: any authenticated user. Writes: system administrators only, audited
per FR-025. DELETE never removes rows: values are deactivated instead
(BR-004, DEF-006); referenced records are additionally protected by FK
on_delete=PROTECT at the database level.
"""

from rest_framework import viewsets
from rest_framework.response import Response

from apps.audit.services import record_audit
from apps.core.permissions import ReferenceDataPermission
from apps.reference_data.models import (
    AssetCondition,
    AssetStatus,
    Category,
    CostCenter,
    Department,
    Location,
    MaintenanceType,
    StatusTransitionRule,
    Supplier,
)
from apps.reference_data.serializers import (
    AssetConditionSerializer,
    AssetStatusSerializer,
    CategorySerializer,
    CostCenterSerializer,
    DepartmentSerializer,
    LocationSerializer,
    MaintenanceTypeSerializer,
    StatusTransitionRuleSerializer,
    SupplierSerializer,
)


def _snapshot(obj) -> dict:
    return {
        "code": getattr(obj, "code", None),
        "name": getattr(obj, "name", getattr(obj, "label", None)),
        "active": obj.active,
    }


class BaseReferenceViewSet(viewsets.ModelViewSet):
    permission_classes = [ReferenceDataPermission]
    lookup_field = "uuid"
    filterset_fields = ["active"]
    ordering = ["code"]

    def _audit(self, request, action: str, obj, before: dict | None, after: dict | None) -> None:
        record_audit(
            actor=request.user,
            action=action,
            target=obj,
            before=before,
            after=after,
            correlation_id=getattr(request, "correlation_id", None),
        )

    def perform_create(self, serializer) -> None:
        obj = serializer.save()
        self._audit(
            self.request,
            f"reference.{obj._meta.model_name}.create",
            obj,
            before=None,
            after=_snapshot(obj),
        )

    def perform_update(self, serializer) -> None:
        before = _snapshot(self.get_object())
        obj = serializer.save()
        self._audit(
            self.request,
            f"reference.{obj._meta.model_name}.update",
            obj,
            before=before,
            after=_snapshot(obj),
        )

    def destroy(self, request, *args, **kwargs) -> Response:
        """BR-004: deactivate-not-delete. Idempotent; returns the updated row."""
        obj = self.get_object()
        before = _snapshot(obj)
        if obj.active:
            obj.active = False
            obj.save(update_fields=["active", "updated_at"])
            self._audit(
                request,
                f"reference.{obj._meta.model_name}.deactivate",
                obj,
                before=before,
                after=_snapshot(obj),
            )
        return Response(self.get_serializer(obj).data, status=200)


class DepartmentViewSet(BaseReferenceViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class LocationViewSet(BaseReferenceViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class CostCenterViewSet(BaseReferenceViewSet):
    queryset = CostCenter.objects.all()
    serializer_class = CostCenterSerializer


class SupplierViewSet(BaseReferenceViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class MaintenanceTypeViewSet(BaseReferenceViewSet):
    queryset = MaintenanceType.objects.all()
    serializer_class = MaintenanceTypeSerializer


class CategoryViewSet(BaseReferenceViewSet):
    queryset = Category.objects.prefetch_related("attribute_definitions")
    serializer_class = CategorySerializer


class AssetStatusViewSet(BaseReferenceViewSet):
    queryset = AssetStatus.objects.all()
    serializer_class = AssetStatusSerializer
    ordering = ["sort_order", "code"]


class AssetConditionViewSet(BaseReferenceViewSet):
    queryset = AssetCondition.objects.all()
    serializer_class = AssetConditionSerializer
    ordering = ["sort_order", "code"]


class StatusTransitionRuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StatusTransitionRule.objects.select_related("from_status", "to_status").order_by(
        "from_status__code", "to_status__code"
    )
    serializer_class = StatusTransitionRuleSerializer
    lookup_field = "uuid"
