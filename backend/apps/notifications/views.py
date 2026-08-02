from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ApiException
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services import MANDATORY_TYPES, OPTIONAL_TYPES


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "uuid",
            "type",
            "title",
            "body",
            "link",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """In-app notification center (FR-023). Users only ever see their own."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # drf-spectacular schema generation
            return Notification.objects.none()
        queryset = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("unread", "").lower() in {"1", "true", "yes"}:
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, uuid=None) -> Response:
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)


class NotificationPreferencesView(APIView):
    """User notification preferences (FR-023). Mandatory compliance types
    cannot be muted."""

    permission_classes = [IsAuthenticated]

    def _payload(self, user) -> dict:
        preference = NotificationPreference.objects.filter(user=user).first()
        return {
            "muted_types": sorted(preference.muted_types) if preference else [],
            "optional_types": sorted(OPTIONAL_TYPES),
            "mandatory_types": sorted(MANDATORY_TYPES),
        }

    def get(self, request) -> Response:
        return Response(self._payload(request.user))

    def patch(self, request) -> Response:
        muted = request.data.get("muted_types")
        if not isinstance(muted, list) or not all(isinstance(item, str) for item in muted):
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "muted_types must be a list of notification type strings.",
                field_errors={"muted_types": ["Provide a list of strings."]},
            )
        blocked = sorted(set(muted) & MANDATORY_TYPES)
        if blocked:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "Mandatory compliance notifications cannot be muted.",
                field_errors={
                    "muted_types": [f"Cannot mute mandatory types: {', '.join(blocked)}."]
                },
            )
        unknown = sorted(set(muted) - OPTIONAL_TYPES - MANDATORY_TYPES)
        if unknown:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "Unknown notification types.",
                field_errors={"muted_types": [f"Unknown types: {', '.join(unknown)}."]},
            )
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        preference.muted_types = sorted(set(muted))
        preference.save(update_fields=["muted_types", "updated_at"])
        return Response(self._payload(request.user))
