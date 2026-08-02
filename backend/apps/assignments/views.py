from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assets.models import Asset
from apps.assignments.models import Assignment, Reservation
from apps.core import capabilities
from apps.core.exceptions import ApiException
from apps.core.permissions import scope_assets


class AssignmentReadSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField()
    custodian = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "uuid",
            "asset",
            "custodian",
            "department",
            "location",
            "assigned_at",
            "expected_return_at",
            "returned_at",
            "acknowledged_at",
            "status",
            "notes",
        ]

    def get_asset(self, obj) -> dict:
        return {"uuid": str(obj.asset.uuid), "tag": obj.asset.tag, "name": obj.asset.name}

    def get_custodian(self, obj) -> dict | None:
        if obj.custodian is None:
            return None
        return {
            "uuid": str(obj.custodian.uuid),
            "username": obj.custodian.username,
            "display_name": obj.custodian.display_name,
        }

    def get_department(self, obj) -> dict | None:
        if obj.department is None:
            return None
        return {"uuid": str(obj.department.uuid), "name": obj.department.name}

    def get_location(self, obj) -> dict | None:
        if obj.location is None:
            return None
        return {"uuid": str(obj.location.uuid), "name": obj.location.name}


class AssignmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Assignment work queue (FR-007; /assignments page). Read-only plus the
    custodian acknowledgement action. Mutations happen on the asset endpoints.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AssignmentReadSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        queryset = Assignment.objects.select_related(
            "asset", "custodian", "department", "location"
        ).order_by("-assigned_at")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        visible = scope_assets(self.request.user, Asset.objects.all())
        queryset = queryset.filter(asset__in=visible)
        status = self.request.query_params.get("status")
        if status == "active":
            queryset = queryset.filter(returned_at__isnull=True)
        elif status == "closed":
            queryset = queryset.filter(returned_at__isnull=False)
        return queryset

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, uuid=None):
        """FR-007: custodian acknowledges receipt of the assignment."""
        assignment = (
            Assignment.objects.select_related("asset", "custodian", "department", "location")
            .filter(uuid=uuid, returned_at__isnull=True)
            .first()
        )
        if assignment is None:
            raise ApiException(404, "NOT_FOUND", "The requested resource was not found.")
        user = request.user
        is_custodian = assignment.custodian_id == user.id
        if not (is_custodian or capabilities.can_write_assets(user)):
            raise ApiException(
                403,
                "PERMISSION_DENIED",
                "Only the custodian or an inventory writer can acknowledge.",
            )
        if assignment.acknowledged_at is None:
            assignment.acknowledged_at = timezone.now()
            assignment.save(update_fields=["acknowledged_at", "updated_at"])
        return Response(self.get_serializer(assignment).data)


class ReservationReadSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField()
    requester = serializers.SerializerMethodField()
    overdue = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "uuid",
            "asset",
            "requester",
            "start_at",
            "end_at",
            "purpose",
            "status",
            "notes",
            "overdue",
        ]

    def get_asset(self, obj) -> dict:
        return {"uuid": str(obj.asset.uuid), "tag": obj.asset.tag, "name": obj.asset.name}

    def get_requester(self, obj) -> dict | None:
        if obj.requester is None:
            return None
        return {
            "uuid": str(obj.requester.uuid),
            "username": obj.requester.username,
            "display_name": obj.requester.display_name,
        }

    def get_overdue(self, obj) -> bool:
        return obj.status in Reservation.ACTIVE_STATUSES and obj.end_at < timezone.now()


class ReservationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Reservation list with overdue identification (FR-010; /reservations page).

    Read-only: reservations are created/checked out via the asset endpoints.
    Scope: reservations on assets visible to the user, plus the user's own
    requests. Filters: ``status``, ``asset`` (uuid), ``requester`` (uuid),
    ``overdue=true``.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReservationReadSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        queryset = Reservation.objects.select_related("asset", "requester").order_by("-start_at")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        user = self.request.user
        visible = scope_assets(user, Asset.objects.all())
        queryset = queryset.filter(Q(asset__in=visible) | Q(requester=user))
        params = self.request.query_params
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("asset"):
            queryset = queryset.filter(asset__uuid=params["asset"])
        if params.get("requester"):
            queryset = queryset.filter(requester__uuid=params["requester"])
        if params.get("overdue", "").lower() in {"1", "true", "yes"}:
            queryset = queryset.filter(
                status__in=Reservation.ACTIVE_STATUSES, end_at__lt=timezone.now()
            )
        return queryset
