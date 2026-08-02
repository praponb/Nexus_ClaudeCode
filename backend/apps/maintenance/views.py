from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assets.models import Asset
from apps.core.idempotency import idempotency_key_from, run_idempotent
from apps.core.permissions import CanEditAsset, scope_assets
from apps.maintenance import services
from apps.maintenance.models import MaintenanceRecord
from apps.maintenance.serializers import (
    MaintenanceCompleteSerializer,
    MaintenanceRecordSerializer,
)


class MaintenanceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Maintenance work list and records (FR-011)."""

    serializer_class = MaintenanceRecordSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = MaintenanceRecord.objects.select_related("asset", "maintenance_type")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        visible = scope_assets(self.request.user, Asset.objects.all())
        queryset = queryset.filter(asset__in=visible)
        params = self.request.query_params
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("asset"):
            queryset = queryset.filter(asset__uuid=params["asset"])
        return queryset

    def get_permissions(self):
        if self.action in {"create", "partial_update", "complete"}:
            return [IsAuthenticated(), CanEditAsset()]
        return [IsAuthenticated()]

    def _respond(self, request, handler):
        key = idempotency_key_from(request)
        if key is None:
            status, body = handler()
            return Response(body, status=status)
        status, body, _ = run_idempotent(
            user=request.user,
            endpoint=f"POST {request.path}",
            key=key,
            request_payload=request.data,
            handler=handler,
        )
        return Response(body, status=status)

    def create(self, request, *args, **kwargs) -> Response:
        asset_uuid = request.data.get("asset")
        visible = scope_assets(request.user, Asset.objects.all())
        asset = visible.filter(uuid=asset_uuid).select_related("status").first()
        if asset is None:
            from apps.core.exceptions import ApiException

            raise ApiException(404, "NOT_FOUND", "The requested resource was not found.")

        def handler() -> tuple[int, dict]:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            record = services.create_record(
                actor=request.user,
                asset=asset,
                correlation_id=getattr(request, "correlation_id", None),
                **data,
            )
            return 201, self.get_serializer(record).data

        return self._respond(request, handler)

    def partial_update(self, request, *args, **kwargs) -> Response:
        record = self.get_object()
        serializer = self.get_serializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = {
            key: value
            for key, value in serializer.validated_data.items()
            if key in {"issue", "provider", "technician", "next_due", "cost", "cost_currency"}
        }
        record = services.update_record(
            actor=request.user,
            record=record,
            data=data,
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, uuid=None) -> Response:
        record = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = MaintenanceCompleteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            completed = services.complete_record(
                actor=request.user,
                record=record,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            return 200, self.get_serializer(completed).data

        return self._respond(request, handler)
