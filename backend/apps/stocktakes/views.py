from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core import capabilities
from apps.core.exceptions import ApiException
from apps.core.idempotency import idempotency_key_from, run_idempotent
from apps.core.permissions import IsManagerOrAdmin
from apps.stocktakes import services
from apps.stocktakes.models import StocktakeObservation, StocktakeSession
from apps.stocktakes.serializers import (
    StocktakeObservationSerializer,
    StocktakeSessionSerializer,
)


class StocktakeViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Stocktake sessions (FR-022)."""

    serializer_class = StocktakeSessionSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return StocktakeSession.objects.prefetch_related("locations", "operators")

    def get_permissions(self):
        if self.action in {"create", "partial_update", "start", "reconcile", "close"}:
            return [IsAuthenticated(), IsManagerOrAdmin()]
        if self.action == "observations":
            return [IsAuthenticated()]
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

    def perform_create(self, serializer) -> None:
        data = dict(serializer.validated_data)
        self._session = services.create_session(
            actor=self.request.user,
            correlation_id=getattr(self.request, "correlation_id", None),
            **data,
        )

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(self._session).data, status=201)

    @action(detail=True, methods=["post"], url_path="observations")
    def observations(self, request, uuid=None) -> Response:
        if not capabilities.can_write_assets(request.user):
            raise ApiException(
                403,
                "PERMISSION_DENIED",
                "Only inventory operators and managers record observations.",
            )
        session = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = StocktakeObservationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            observation = services.record_observation(
                actor=request.user,
                session=session,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            return 201, StocktakeObservationSerializer(observation).data

        return self._respond(request, handler)

    @observations.mapping.get
    def list_observations(self, request, uuid=None) -> Response:
        session = self.get_object()
        queryset = session.observations.select_related("asset", "location", "condition")
        page = self.paginate_queryset(queryset)
        rows = StocktakeObservationSerializer(page or queryset[:100], many=True).data
        if page is not None:
            return self.get_paginated_response(rows)
        return Response({"results": rows})

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, uuid=None) -> Response:
        session = services.start_session(
            actor=request.user,
            session=self.get_object(),
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"], url_path="reconcile")
    def reconcile(self, request, uuid=None) -> Response:
        session = services.reconcile_session(
            actor=request.user,
            session=self.get_object(),
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, uuid=None) -> Response:
        session = services.close_session(
            actor=request.user,
            session=self.get_object(),
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["get"], url_path="variance")
    def variance(self, request, uuid=None) -> Response:
        return Response(services.compute_variance(self.get_object()))


# Observations listing is also exposed via the action above; the model is
# imported here for the OpenAPI component registry.
_ = StocktakeObservation
