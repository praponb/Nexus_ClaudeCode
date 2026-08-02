"""Maintenance application services (FR-011/FR-012).

Open work keeps the asset Under Maintenance; completion records the result,
updates last/next maintenance dates, and returns the asset to service.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.assets.models import Asset, LifecycleEvent
from apps.assets.services import snapshot, transition_status
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.maintenance.models import MaintenanceRecord


def _lock_asset(asset: Asset) -> Asset:
    return Asset.objects.select_for_update().select_related("status").get(pk=asset.pk)


def _lifecycle(asset, actor, event_type, summary, details=None, correlation_id=None):
    LifecycleEvent.objects.create(
        asset=asset,
        event_type=event_type,
        actor=actor,
        occurred_at=timezone.now(),
        summary=summary,
        details=details or {},
        correlation_id=correlation_id,
    )


def create_record(
    *,
    actor,
    asset: Asset,
    maintenance_type,
    issue: str = "",
    provider: str = "",
    technician: str = "",
    cost=None,
    cost_currency: str = "",
    next_due=None,
    correlation_id=None,
) -> MaintenanceRecord:
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        if locked.maintenance_records.filter(status=MaintenanceRecord.Status.OPEN).exists():
            raise ApiException(
                409,
                "MAINTENANCE_ALREADY_OPEN",
                "This asset already has an open maintenance record.",
            )
        record = MaintenanceRecord.objects.create(
            asset=locked,
            maintenance_type=maintenance_type,
            issue=issue,
            provider=provider,
            technician=technician,
            cost=cost,
            cost_currency=cost_currency if cost is not None else "",
            next_due=next_due,
        )
        transition_status(
            actor=actor,
            asset=locked,
            to_code="under_maintenance",
            correlation_id=correlation_id,
            event_type="maintenance_started",
            summary=f"Asset {locked.tag} entered maintenance ({maintenance_type.name}).",
            details={"record_uuid": str(record.uuid)},
        )
        record_audit(
            actor=actor,
            action="maintenance.create",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return record


def update_record(*, actor, record: MaintenanceRecord, data: dict, correlation_id=None):
    if record.status != MaintenanceRecord.Status.OPEN:
        raise ApiException(
            409,
            "MAINTENANCE_NOT_OPEN",
            "Only open maintenance records can be edited.",
        )
    with transaction.atomic():
        for field_name, value in data.items():
            setattr(record, field_name, value)
        record.save()
        _lifecycle(
            record.asset,
            actor,
            "maintenance_updated",
            f"Maintenance record updated for {record.asset.tag}.",
            {"record_uuid": str(record.uuid), "fields": sorted(data)},
            correlation_id,
        )
        record_audit(
            actor=actor,
            action="maintenance.update",
            target=record.asset,
            after={"record_uuid": str(record.uuid), "fields": sorted(data)},
            correlation_id=correlation_id,
        )
    return record


def complete_record(
    *,
    actor,
    record: MaintenanceRecord,
    result: str = "",
    next_due=None,
    cost=None,
    cost_currency: str = "",
    correlation_id=None,
) -> MaintenanceRecord:
    with transaction.atomic():
        if record.status != MaintenanceRecord.Status.OPEN:
            raise ApiException(
                409,
                "MAINTENANCE_NOT_OPEN",
                "This maintenance record is not open.",
            )
        locked = _lock_asset(record.asset)
        before = snapshot(locked)
        today = timezone.now().date()
        record.status = MaintenanceRecord.Status.COMPLETED
        record.completed_at = timezone.now()
        record.result = result
        if cost is not None:
            record.cost = cost
            record.cost_currency = cost_currency
        if next_due is None and locked.maintenance_interval_months:
            next_due = today + timedelta(days=30 * locked.maintenance_interval_months)
        record.next_due = next_due
        record.save()
        locked.last_maintenance_date = today
        locked.next_maintenance_due = next_due
        locked.save(update_fields=["last_maintenance_date", "next_maintenance_due", "updated_at"])
        back_to = (
            "assigned"
            if locked.assignments.filter(returned_at__isnull=True).exists()
            else "available"
        )
        transition_status(
            actor=actor,
            asset=locked,
            to_code=back_to,
            correlation_id=correlation_id,
            event_type="maintenance_completed",
            summary=f"Asset {locked.tag} maintenance completed; returned to service.",
            details={"record_uuid": str(record.uuid)},
        )
        record_audit(
            actor=actor,
            action="maintenance.complete",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return record
