import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import mfa
from apps.accounts.serializers import MeSerializer
from apps.audit.services import record_audit
from apps.core import login_guard
from apps.core.client_ip import client_ip
from apps.core.exceptions import ApiException
from apps.core.throttling import ScopedSimpleRateThrottle

logger = logging.getLogger(__name__)

GENERIC_LOGIN_FAILURE = "Invalid username or password."
GENERIC_MFA_FAILURE = "That code is not valid. Check your authenticator and try again."


class LoginThrottle(ScopedSimpleRateThrottle):
    """Rate limit on login attempts (NFR-007)."""

    scope = "login"


class MfaThrottle(ScopedSimpleRateThrottle):
    """Rate limit on second-factor submission.

    A TOTP code is only six digits, so the verify step needs its own ceiling --
    the login throttle does not apply here (the password step already passed).
    """

    scope = "mfa"


def _complete_login(request, user, extra: dict | None = None) -> Response:
    """Finish a fully-authenticated sign-in."""
    mfa.clear_pending(request)
    login(request, user)  # rotates the session key
    record_audit(
        actor=user,
        action="auth.login",
        target=user,
        outcome="success",
        correlation_id=getattr(request, "correlation_id", None),
        ip_address=client_ip(request),
    )
    return Response({"user": MeSerializer(user).data, **(extra or {})})


def _pending_or_401(request):
    """The user mid-sign-in, or a 401 if that window has closed."""
    user = mfa.pending_user(request)
    if user is None:
        raise ApiException(
            401,
            "MFA_PENDING_EXPIRED",
            "Your sign-in attempt expired. Start again.",
        )
    return user


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
        # Per-account guard. LoginThrottle already bounds one IP; this bounds the
        # guesses a single account can receive from any number of addresses.
        if login_guard.is_locked(username):
            record_audit(
                actor=None,
                actor_type="user",
                action="auth.login",
                after={"username": username, "reason": "locked"},
                outcome="failure",
                correlation_id=getattr(request, "correlation_id", None),
                ip_address=client_ip(request),
            )
            raise ApiException(
                429,
                "ACCOUNT_LOCKED",
                "Too many failed sign-in attempts. Try again later.",
                retryable=True,
            )

        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            # Counted for unknown usernames too, so a lockout never reveals
            # which accounts exist (FR-001).
            login_guard.record_failure(username)
            record_audit(
                actor=None,
                actor_type="user",
                action="auth.login",
                after={"username": username},
                outcome="failure",
                correlation_id=getattr(request, "correlation_id", None),
                ip_address=client_ip(request),
            )
            # Generic message: do not reveal whether the account exists (FR-001).
            raise ApiException(401, "AUTHENTICATION_FAILED", GENERIC_LOGIN_FAILURE)

        login_guard.reset(username)

        # Password is correct but may not be sufficient. Deliberately do NOT
        # call login() yet: until the second factor is satisfied the caller
        # holds only a pending marker and is still unauthenticated.
        if mfa.mfa_required(user):
            device = mfa.confirmed_device(user)
            stage = "verify" if device is not None else "setup"
            mfa.start_pending(request, user, stage)
            record_audit(
                actor=user,
                action="auth.login",
                target=user,
                after={"stage": f"mfa_{stage}"},
                outcome="pending",
                correlation_id=getattr(request, "correlation_id", None),
                ip_address=client_ip(request),
            )
            return Response({"mfa_required": True, "stage": stage})

        return _complete_login(request, user)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        record_audit(
            actor=request.user,
            action="auth.logout",
            target=request.user,
            outcome="success",
            correlation_id=getattr(request, "correlation_id", None),
            ip_address=client_ip(request),
        )
        logout(request)
        return Response(status=204)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        return Response(MeSerializer(request.user).data)


class MfaSetupView(APIView):
    """Enrolment payload for a user who has passed the password step.

    Reachable only with a live pending sign-in, never anonymously: the secret
    is a credential.
    """

    permission_classes = [AllowAny]
    throttle_classes = [MfaThrottle]

    def post(self, request) -> Response:
        user = _pending_or_401(request)
        if mfa.confirmed_device(user) is not None:
            raise ApiException(
                409,
                "MFA_ALREADY_ENROLLED",
                "This account already has an authenticator enrolled.",
            )
        device = mfa.get_or_create_pending_device(user)
        uri = mfa.provisioning_uri(device)
        return Response(
            {
                "secret": device.secret,
                "provisioning_uri": uri,
                "qr_svg": mfa.qr_svg(uri),
                "issuer": settings.MFA_ISSUER,
                "account": user.username,
            }
        )


class MfaConfirmView(APIView):
    """Activate a freshly enrolled authenticator and finish signing in."""

    permission_classes = [AllowAny]
    throttle_classes = [MfaThrottle]

    def post(self, request) -> Response:
        user = _pending_or_401(request)
        code = str(request.data.get("code", "") or "")
        device = mfa.TotpDevice.objects.filter(user=user).first()
        if device is None:
            raise ApiException(400, "MFA_NOT_STARTED", "Start enrolment first.")
        if device.is_confirmed:
            raise ApiException(
                409,
                "MFA_ALREADY_ENROLLED",
                "This account already has an authenticator enrolled.",
            )
        if not mfa.verify_code(device, code):
            raise ApiException(400, "MFA_INVALID_CODE", GENERIC_MFA_FAILURE)

        device.confirmed_at = timezone.now()
        device.save(update_fields=["confirmed_at"])
        # Shown exactly once -- only hashes are stored.
        codes = mfa.issue_recovery_codes(device)
        record_audit(
            actor=user,
            action="auth.mfa.enroll",
            target=user,
            outcome="success",
            correlation_id=getattr(request, "correlation_id", None),
            ip_address=client_ip(request),
        )
        return _complete_login(request, user, {"recovery_codes": codes})


class MfaVerifyView(APIView):
    """Second factor for an already-enrolled user."""

    permission_classes = [AllowAny]
    throttle_classes = [MfaThrottle]

    def post(self, request) -> Response:
        user = _pending_or_401(request)
        device = mfa.confirmed_device(user)
        if device is None:
            raise ApiException(400, "MFA_NOT_ENROLLED", "No authenticator is enrolled.")

        code = str(request.data.get("code", "") or "")
        recovery = str(request.data.get("recovery_code", "") or "")
        used_recovery = False
        if recovery:
            used_recovery = mfa.consume_recovery_code(device, recovery)
            ok = used_recovery
        else:
            ok = mfa.verify_code(device, code)

        if not ok:
            # Counted against the same per-account budget as password failures,
            # so a correct password plus code-guessing cannot run unbounded.
            login_guard.record_failure(user.username)
            record_audit(
                actor=user,
                action="auth.mfa.verify",
                target=user,
                outcome="failure",
                correlation_id=getattr(request, "correlation_id", None),
                ip_address=client_ip(request),
            )
            raise ApiException(400, "MFA_INVALID_CODE", GENERIC_MFA_FAILURE)

        login_guard.reset(user.username)
        record_audit(
            actor=user,
            action="auth.mfa.verify",
            target=user,
            after={"method": "recovery_code" if used_recovery else "totp"},
            outcome="success",
            correlation_id=getattr(request, "correlation_id", None),
            ip_address=client_ip(request),
        )
        extra: dict = {}
        if used_recovery:
            extra["recovery_codes_remaining"] = mfa.unused_recovery_code_count(device)
        return _complete_login(request, user, extra)
