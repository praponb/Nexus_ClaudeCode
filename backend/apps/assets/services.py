"""Asset application services.

All multi-record mutations run in a transaction and emit LifecycleEvent +
AuditEvent atomically (design section 9.2; FR-003/FR-004; BR-003/BR-009).
"""

from django.db import transaction
from django.utils import timezone

from apps.assets.models import Asset, AssetTagSequence, LifecycleEvent
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.reference_data.models import AssetStatus, StatusTransitionRule

TAG_PREFIX = "AST"

SNAPSHOT_SCALAR_FIELDS = (
    "tag",
    "name",
    "serial_number",
    "manufacturer",
    "model",
    "record_status",
    "data_quality_status",
)
SNAPSHOT_RELATED_FIELDS = ("category", "status", "condition", "department", "location", "custodian")


def generate_next_tag(prefix: str = TAG_PREFIX) -> str:
    with transaction.atomic():
        sequence, _ = AssetTagSequence.objects.select_for_update().get_or_create(
            prefix=prefix, defaults={"next_value": 1}
        )
        value = sequence.next_value
        sequence.next_value = value + 1
        sequence.save(update_fields=["next_value"])
    return f"{prefix}-{value:06d}"


def default_status() -> AssetStatus | None:
    status = AssetStatus.objects.filter(code="in_stock", active=True).first()
    if status is None:
        status = AssetStatus.objects.filter(active=True).order_by("sort_order", "code").first()
    return status


def snapshot(asset: Asset) -> dict:
    data: dict = {}
    for field_name in SNAPSHOT_SCALAR_FIELDS:
        data[field_name] = getattr(asset, field_name)
    for field_name in SNAPSHOT_RELATED_FIELDS:
        related = getattr(asset, field_name)
        data[field_name] = str(related.uuid) if related is not None else None
    return data


def _check_legal_hold(actor, data: dict) -> None:
    """FR-030: only system administrators may set or clear the legal hold."""
    if "legal_hold" in data and getattr(actor, "role", "") != "system_admin":
        raise ApiException(
            403,
            "PERMISSION_DENIED",
            "Only system administrators may change the legal hold.",
        )


def transition_status(
    *,
    actor,
    asset: Asset,
    to_code: str,
    correlation_id=None,
    event_type: str = "status_changed",
    summary: str | None = None,
    details: dict | None = None,
    check_role: bool = True,
    save: bool = True,
) -> None:
    """Validated status transition for lifecycle workflows.

    The caller must hold a row lock on ``asset``. Validates the transition
    rules (and the actor's role unless ``check_role=False`` for flows whose
    permission model is endpoint-based, e.g. employee exception reports),
    then emits a LifecycleEvent. Audit is the caller's responsibility.
    """
    old_status = asset.status
    if old_status.code == to_code:
        return
    if old_status.is_terminal:
        raise ApiException(
            409,
            "STATUS_TRANSITION_INVALID",
            f"Assets in terminal status '{old_status.label}' cannot change status.",
        )
    new_status = AssetStatus.objects.filter(code=to_code).first()
    if new_status is None:
        raise ApiException(
            409,
            "STATUS_TRANSITION_INVALID",
            f"Target status '{to_code}' is not configured.",
        )
    rule = StatusTransitionRule.objects.filter(from_status=old_status, to_status=new_status).first()
    if rule is None:
        raise ApiException(
            409,
            "STATUS_TRANSITION_INVALID",
            f"Transition from '{old_status.label}' to '{new_status.label}' is not allowed.",
        )
    if check_role and rule.allowed_roles and actor.role not in rule.allowed_roles:
        raise ApiException(
            403,
            "PERMISSION_DENIED",
            "Your role is not permitted to perform this status transition.",
        )
    asset.status = new_status
    if save:
        asset.save(update_fields=["status", "updated_at"])
    LifecycleEvent.objects.create(
        asset=asset,
        event_type=event_type,
        actor=actor,
        occurred_at=timezone.now(),
        summary=summary or f"Status changed from {old_status.label} to {new_status.label}.",
        details=details if details is not None else {"from": old_status.code, "to": to_code},
        correlation_id=correlation_id,
    )


def create_asset(*, actor, data: dict, correlation_id=None) -> Asset:
    _check_legal_hold(actor, data)
    with transaction.atomic():
        tag = (data.pop("tag", "") or "").strip()
        if not tag:
            tag = generate_next_tag()
        elif Asset.objects.filter(tag__iexact=tag).exists():
            raise ApiException(
                409,
                "DUPLICATE_TAG",
                "An asset with this tag already exists.",
                field_errors={"tag": ["Asset tag must be unique across all assets."]},
            )
        if data.get("status") is None:
            status = default_status()
            if status is None:
                raise ApiException(
                    400,
                    "VALIDATION_FAILED",
                    "Asset statuses are not configured.",
                    field_errors={
                        "status": ["No asset statuses exist. Ask an administrator to seed them."]
                    },
                )
            data["status"] = status
        asset = Asset(tag=tag, created_by=actor, updated_by=actor, **data)
        asset.save()
        LifecycleEvent.objects.create(
            asset=asset,
            event_type="registered",
            actor=actor,
            occurred_at=timezone.now(),
            summary=f"Asset {asset.tag} registered.",
            details={"tag": asset.tag},
            correlation_id=correlation_id,
        )
        record_audit(
            actor=actor,
            action="asset.create",
            target=asset,
            after=snapshot(asset),
            correlation_id=correlation_id,
        )
    return asset


def update_asset(
    *, actor, asset: Asset, data: dict, expected_version: int, correlation_id=None
) -> Asset:
    data.pop("version", None)
    _check_legal_hold(actor, data)
    with transaction.atomic():
        locked = Asset.objects.select_for_update().select_related("status").get(pk=asset.pk)
        if locked.version != expected_version:
            raise ApiException(
                409,
                "VERSION_CONFLICT",
                "This asset was changed by someone else. Reload it and reapply your changes.",
            )
        before = snapshot(locked)
        old_status = locked.status
        new_status = data.get("status") or old_status
        if new_status != old_status:
            # Validated transition + lifecycle event; field applied below.
            transition_status(
                actor=actor,
                asset=locked,
                to_code=new_status.code,
                correlation_id=correlation_id,
                save=False,
            )
            data = {key: value for key, value in data.items() if key != "status"}
        for field_name, value in data.items():
            setattr(locked, field_name, value)
        locked.version = locked.version + 1
        locked.updated_by = actor
        locked.save()
        record_audit(
            actor=actor,
            action="asset.update",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return locked


def find_duplicate_warnings(
    *,
    serial_number: str = "",
    manufacturer: str = "",
    model: str = "",
    exclude_uuid=None,
) -> list[dict]:
    """Non-blocking duplicate detection (BR-008)."""
    warnings: list[dict] = []
    queryset = Asset.objects.filter(record_status="active")
    if exclude_uuid is not None:
        queryset = queryset.exclude(uuid=exclude_uuid)

    def _matches(matches) -> list[dict]:
        return [{"uuid": str(m.uuid), "tag": m.tag, "name": m.name} for m in matches]

    if serial_number:
        matches = list(queryset.filter(serial_number__iexact=serial_number)[:5])
        if matches:
            warnings.append(
                {
                    "code": "POSSIBLE_DUPLICATE_SERIAL",
                    "message": (
                        f"{len(matches)} active asset(s) already use serial number "
                        f"'{serial_number}'."
                    ),
                    "matches": _matches(matches),
                }
            )
    if manufacturer and model:
        matches = list(queryset.filter(manufacturer__iexact=manufacturer, model__iexact=model)[:5])
        if matches:
            warnings.append(
                {
                    "code": "SIMILAR_MANUFACTURER_MODEL",
                    "message": (
                        f"{len(matches)} active asset(s) share manufacturer "
                        f"'{manufacturer}' and model '{model}'."
                    ),
                    "matches": _matches(matches),
                }
            )
    return warnings
