import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import MeSerializer
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.core.throttling import ScopedSimpleRateThrottle

logger = logging.getLogger(__name__)

GENERIC_LOGIN_FAILURE = "Invalid username or password."


class LoginThrottle(ScopedSimpleRateThrottle):
    """Rate limit on login attempts (NFR-007)."""

    scope = "login"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class CsrfTokenView(APIView):
    """SPA fetches this first; sets the ``csrftoken`` cookie (design section 12)."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request) -> Response:
        return Response({"detail": "CSRF cookie set."})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request) -> Response:
        if not settings.LOCAL_AUTH_ENABLED:
            raise ApiException(
                403,
                "LOCAL_AUTH_DISABLED",
                "Local sign-in is disabled. Use single sign-on.",
            )
        username = str(request.data.get("username", "") or "").strip()
        password = str(request.data.get("password", "") or "")
        if not username or not password:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "Username and password are required.",
                field_errors={
                    "username": ["This field is required."] if not username else [],
                    "password": ["This field is required."] if not password else [],
                },
            )
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            record_audit(
                actor=None,
                actor_type="user",
                action="auth.login",
                after={"username": username},
                outcome="failure",
                correlation_id=getattr(request, "correlation_id", None),
                ip_address=_client_ip(request),
            )
            # Generic message: do not reveal whether the account exists (FR-001).
            raise ApiException(401, "AUTHENTICATION_FAILED", GENERIC_LOGIN_FAILURE)
        login(request, user)  # rotates the session key
        record_audit(
            actor=user,
            action="auth.login",
            target=user,
            outcome="success",
            correlation_id=getattr(request, "correlation_id", None),
            ip_address=_client_ip(request),
        )
        return Response({"user": MeSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        record_audit(
            actor=request.user,
            action="auth.logout",
            target=request.user,
            outcome="success",
            correlation_id=getattr(request, "correlation_id", None),
            ip_address=_client_ip(request),
        )
        logout(request)
        return Response(status=204)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        return Response(MeSerializer(request.user).data)
