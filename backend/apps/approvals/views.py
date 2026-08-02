from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.approvals import services
from apps.approvals.models import ApprovalRequest
from apps.approvals.serializers import ApprovalDecisionSerializer, ApprovalSerializer
from apps.assets.models import Asset
from apps.core.exceptions import ApiException
from apps.core.permissions import scope_assets


class ApprovalViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Approval inbox (FR-024). Requests on assets visible to the user plus
    the user's own requests; decisions require an approver role."""

    serializer_class = ApprovalSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = ApprovalRequest.objects.select_related("asset", "requester", "approver")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        user = self.request.user
        visible = scope_assets(user, Asset.objects.all())
        queryset = queryset.filter(Q(asset__in=visible) | Q(requester=user))
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_permissions(self):
        return [IsAuthenticated()]

    def _decide(self, request, decision: str) -> Response:
        approval = self.get_object()
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decided = services.decide(
            request=approval,
            actor=request.user,
            decision=decision,
            comments=serializer.validated_data.get("comments", ""),
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(self.get_serializer(decided).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, uuid=None) -> Response:
        return self._decide(request, ApprovalRequest.Status.APPROVED)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, uuid=None) -> Response:
        return self._decide(request, ApprovalRequest.Status.REJECTED)

    @action(detail=True, methods=["post"], url_path="return")
    def return_request(self, request, uuid=None) -> Response:
        return self._decide(request, ApprovalRequest.Status.RETURNED)


# Imported for the OpenAPI component registry.
_ = ApiException
