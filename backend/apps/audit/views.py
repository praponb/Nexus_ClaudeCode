"""Audit event query API (FR-025; design §11.3 Admin group).

Read-only, restricted to roles holding the ``audit.read`` capability
(system administrators and auditors). No mutation surface exists anywhere
in the application for audit rows.
"""

from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.audit.models import AuditEvent
from apps.core import capabilities


class CanReadAudit(BasePermission):
    message = "You do not have permission to read the audit log."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and "audit.read" in capabilities.capabilities_for(user)
        )


class AuditEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "uuid",
            "actor",
            "actor_type",
            "action",
            "target_type",
            "target_uuid",
            "before",
            "after",
            "outcome",
            "correlation_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor(self, obj) -> dict | None:
        if obj.actor is None:
            return None
        return {"uuid": str(obj.actor.uuid), "username": obj.actor.username}


class AuditEventViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Searchable audit history for authorized users (FR-025)."""

    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, CanReadAudit]
    lookup_field = "uuid"
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("actor").order_by("-id")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        params = self.request.query_params
        if params.get("action"):
            queryset = queryset.filter(action__icontains=params["action"])
        if params.get("target_type"):
            queryset = queryset.filter(target_type=params["target_type"])
        if params.get("target_uuid"):
            queryset = queryset.filter(target_uuid=params["target_uuid"])
        if params.get("correlation_id"):
            queryset = queryset.filter(correlation_id=params["correlation_id"])
        if params.get("actor"):
            queryset = queryset.filter(actor__uuid=params["actor"])
        if params.get("outcome"):
            queryset = queryset.filter(outcome=params["outcome"])
        return queryset
