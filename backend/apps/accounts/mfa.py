"""TOTP second factor for privileged sign-in (design section 12, NFR-007).

Built on ``pyotp`` (RFC 6238) rather than django-otp/django-axes: it is pure
Python with no framework coupling, so it carries no Django-version risk. The
enrolment QR reuses the ``qrcode`` dependency already used for asset labels.

The flow deliberately never calls ``django.contrib.auth.login`` until the second
factor is satisfied. Between the two steps the user is held in an unauthenticated
session carrying only a pending user id and a deadline, so a correct password
alone grants no access to anything.
"""

import secrets
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.accounts.models import MfaRecoveryCode, TotpDevice

RECOVERY_CODE_COUNT = 10
#: Minutes a half-finished sign-in may sit between password and second factor.
PENDING_TTL_SECONDS = 300
#: Accept the adjacent time-steps too, for clock drift between phone and server.
TOTP_VALID_WINDOW = 1


def mfa_required(user) -> bool:
    """True when this user's role obliges them to hold a second factor."""
    required = set(getattr(settings, "MFA_REQUIRED_ROLES", []))
    return bool(required) and getattr(user, "role", "") in required


def confirmed_device(user) -> TotpDevice | None:
    device = TotpDevice.objects.filter(user=user, confirmed_at__isnull=False).first()
    return device


def get_or_create_pending_device(user) -> TotpDevice:
    """Device for enrolment. A new secret is issued until one is confirmed."""
    device = TotpDevice.objects.filter(user=user).first()
    if device is not None and device.is_confirmed:
        return device
    if device is None:
        device = TotpDevice(user=user)
    # Unconfirmed enrolments get a fresh secret each time setup is opened, so an
    # abandoned half-enrolment leaves nothing usable behind.
    device.secret = pyotp.random_base32()
    device.last_used_step = None
    device.save()
    return device


def provisioning_uri(device: TotpDevice) -> str:
    """otpauth:// URI for an authenticator app to scan."""
    issuer = getattr(settings, "MFA_ISSUER", "Asset Inventory")
    return pyotp.TOTP(device.secret).provisioning_uri(
        name=device.user.username,
        issuer_name=issuer,
    )


def qr_svg(uri: str) -> str:
    """Enrolment QR as inline SVG (same approach as the asset label endpoint)."""
    import qrcode
    import qrcode.image.svg

    image = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    return image.to_string().decode("utf-8")


def verify_code(device: TotpDevice, code: str) -> bool:
    """Check a TOTP code, rejecting any code at or before the last one spent.

    The candidate steps are walked explicitly rather than calling
    ``totp.verify``, because we need to know *which* step matched. Recording the
    matched step -- not simply "now" -- is what lets a newer code still be
    accepted inside the same wall-clock window while a replayed one is refused.
    """
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit():
        return False

    totp = pyotp.TOTP(device.secret)
    current_step = int(timezone.now().timestamp()) // totp.interval

    matched: int | None = None
    for offset in range(-TOTP_VALID_WINDOW, TOTP_VALID_WINDOW + 1):
        step = current_step + offset
        if secrets.compare_digest(totp.at(step * totp.interval), code):
            matched = step
            break
    if matched is None:
        return False

    if device.last_used_step is not None and matched <= device.last_used_step:
        # Already spent: a code stays valid for a whole step (plus drift), so
        # without this anyone who observed it could reuse it inside that window.
        return False

    device.last_used_step = matched
    device.save(update_fields=["last_used_step"])
    return True


def issue_recovery_codes(device: TotpDevice) -> list[str]:
    """Replace any existing codes and return the new ones in plaintext once."""
    device.recovery_codes.all().delete()
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(RECOVERY_CODE_COUNT)]
    MfaRecoveryCode.objects.bulk_create(
        [MfaRecoveryCode(device=device, code_hash=make_password(code)) for code in codes]
    )
    return codes


def consume_recovery_code(device: TotpDevice, code: str) -> bool:
    """Spend one unused recovery code; each works exactly once."""
    candidate = (code or "").strip().lower()
    if not candidate:
        return False
    for recovery in device.recovery_codes.filter(used_at__isnull=True):
        if check_password(candidate, recovery.code_hash):
            recovery.used_at = timezone.now()
            recovery.save(update_fields=["used_at"])
            return True
    return False


def unused_recovery_code_count(device: TotpDevice) -> int:
    return device.recovery_codes.filter(used_at__isnull=True).count()


# -- Pending (password-done, factor-outstanding) session -----------------------

SESSION_USER_ID = "mfa_pending_user_id"
SESSION_DEADLINE = "mfa_pending_deadline"
SESSION_STAGE = "mfa_pending_stage"


def start_pending(request, user, stage: str) -> None:
    request.session[SESSION_USER_ID] = user.pk
    request.session[SESSION_STAGE] = stage
    request.session[SESSION_DEADLINE] = (
        timezone.now() + timedelta(seconds=PENDING_TTL_SECONDS)
    ).isoformat()


def clear_pending(request) -> None:
    for key in (SESSION_USER_ID, SESSION_STAGE, SESSION_DEADLINE):
        request.session.pop(key, None)


def pending_user(request):
    """The user mid-sign-in, or None if there is no live pending step."""
    from django.contrib.auth import get_user_model

    user_id = request.session.get(SESSION_USER_ID)
    deadline = request.session.get(SESSION_DEADLINE)
    if not user_id or not deadline:
        return None
    try:
        expires_at = timezone.datetime.fromisoformat(deadline)
    except ValueError:
        clear_pending(request)
        return None
    if timezone.now() > expires_at:
        clear_pending(request)
        return None
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        clear_pending(request)
    return user


def pending_stage(request) -> str:
    return str(request.session.get(SESSION_STAGE, "") or "")
