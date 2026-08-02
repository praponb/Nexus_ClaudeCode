"""Notification dispatch (FR-023).

In-app notifications are always recorded (subject to user preferences and
dedupe). Email is sent only when SMTP is configured; delivery failures are
logged without confidential content. Mandatory types cannot be muted.
"""

import logging

from django.conf import settings

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationPreference

logger = logging.getLogger(__name__)

# Optional notification event types (user-mutable via preferences).
OPTIONAL_TYPES = frozenset(
    {
        "assignment.created",
        "exception.reported",
        "approval.requested",
        "maintenance.due",
        "warranty.expiring",
    }
)
# Mandatory compliance notifications: non-disableable (FR-023).
MANDATORY_TYPES = frozenset({"approval.decided", "compliance.notice"})


def is_muted(user, notification_type: str) -> bool:
    if notification_type in MANDATORY_TYPES:
        return False
    preference = NotificationPreference.objects.filter(user=user).first()
    if preference is None:
        return False
    return notification_type in (preference.muted_types or [])


def notify(
    *,
    recipient,
    type: str,
    title: str,
    body: str = "",
    link: str = "",
    dedupe_key: str = "",
) -> Notification | None:
    """Create an in-app notification (deduped, preference-aware) and attempt
    email delivery when SMTP is configured. Returns the notification, the
    existing unread deduplicated one, or None when muted."""
    if recipient is None or not recipient.is_active:
        return None
    if is_muted(recipient, type):
        return None
    if dedupe_key:
        existing = Notification.objects.filter(
            recipient=recipient, dedupe_key=dedupe_key, read_at__isnull=True
        ).first()
        if existing is not None:
            return existing
    notification = Notification.objects.create(
        recipient=recipient,
        type=type,
        title=title[:255],
        body=body,
        link=link,
        dedupe_key=dedupe_key,
    )
    _send_email(recipient, notification)
    return notification


def notify_roles(
    *,
    roles: set[str],
    type: str,
    title: str,
    body: str = "",
    link: str = "",
    dedupe_key: str = "",
) -> int:
    """Notify every active user holding one of ``roles``. Returns the count
    of newly created notifications (dedupe hits are not recounted)."""
    created = 0
    for user in User.objects.filter(role__in=roles, is_active=True):
        if (
            dedupe_key
            and Notification.objects.filter(
                recipient=user, dedupe_key=dedupe_key, read_at__isnull=True
            ).exists()
        ):
            continue
        result = notify(
            recipient=user, type=type, title=title, body=body, link=link, dedupe_key=dedupe_key
        )
        if result is not None:
            created += 1
    return created


def _send_email(recipient, notification: Notification) -> None:
    """Email delivery when SMTP is configured; failures are logged without
    confidential content (FR-023/NFR-011)."""
    if not getattr(settings, "EMAIL_HOST", "") or not recipient.email:
        return
    try:
        from django.core.mail import send_mail

        send_mail(
            notification.title,
            notification.body or notification.title,
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001 - never leak content; log metadata only
        logger.warning(
            "Email delivery failed for notification %s (recipient id %s)",
            notification.uuid,
            recipient.pk,
        )


def generate_due_reminders(*, today=None) -> dict:
    """Periodic job (Celery task): warranty-expiry and maintenance-due
    reminders to asset/system managers. Deduped per asset per day."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.assets.models import Asset

    day = today or timezone.now().date()
    counts = {"warranty.expiring": 0, "maintenance.due": 0}
    warranty_assets = Asset.objects.filter(
        record_status="active",
        warranty_end__gte=day,
        warranty_end__lte=day + timedelta(days=30),
    )
    for asset in warranty_assets.iterator():
        counts["warranty.expiring"] += notify_roles(
            roles={"system_admin", "asset_manager"},
            type="warranty.expiring",
            title=f"Warranty expiring: {asset.tag}",
            body=f"Warranty for {asset.tag} ({asset.name}) ends on {asset.warranty_end}.",
            link=f"/assets/{asset.uuid}",
            dedupe_key=f"warranty:{asset.uuid}:{day.isoformat()}",
        )
    due_assets = Asset.objects.filter(
        record_status="active",
        next_maintenance_due__isnull=False,
        next_maintenance_due__lte=day,
    )
    for asset in due_assets.iterator():
        due_on = asset.next_maintenance_due
        counts["maintenance.due"] += notify_roles(
            roles={"system_admin", "asset_manager"},
            type="maintenance.due",
            title=f"Maintenance due: {asset.tag}",
            body=f"Maintenance for {asset.tag} ({asset.name}) was due on {due_on}.",
            link=f"/assets/{asset.uuid}",
            dedupe_key=f"maintenance:{asset.uuid}:{day.isoformat()}",
        )
    return counts
