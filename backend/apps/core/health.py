"""Unauthenticated infrastructure health endpoints (NFR-005).

These expose no application data - only coarse liveness/readiness status.
"""

from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LivenessView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        return Response({"status": "ok"})


class ReadinessView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:  # noqa: BLE001 - readiness must not leak internals
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ready"})
