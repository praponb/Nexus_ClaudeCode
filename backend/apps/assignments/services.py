"""Lifecycle workflow services: assignment, transfer, return, reservation,
checkout, exception reports, and retirement/disposal (FR-007…FR-010, FR-013,
FR-014). Approval-gated actions route through FR-024 when the transition rule
requires it.

Every service runs in a single transaction with a row lock on the asset and
emits LifecycleEvent + AuditEvent atomically (design section 9.2).
"""

from django.db import transaction
from django.utils import timezone

from apps.assets.models import Asset, LifecycleEvent
from apps.assets.services import snapshot, transition_status
from apps.assignments.models import Assignment, ExceptionReport, Reservation, TransferRecord
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.notifications.services import notify, notify_roles
from apps.reference_data.models import AssetCondition, AssetStatus

DISPOSAL_OVERRIDE_ROLES = {"system_admin", "asset_manager"}


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


def assign_asset(
    *,
    actor,
    asset: Asset,
    custodian=None,
    department=None,
    location=None,
    expected_return_at=None,
    notes: str = "",
    correlation_id=None,
) -> Assignment:
    """FR-007: assign to a custodian/department/location, closing any prior
    active assignment atomically (BR-002)."""
    if not any([custodian, department, location]):
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "Provide a custodian, department, or location for the assignment.",
            field_errors={"custodian": ["A custodian, department, or location is required."]},
        )
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        previous = locked.assignments.filter(returned_at__isnull=True).first()
        if previous is not None:
            previous.returned_at = timezone.now()
            previous.status = Assignment.Status.CLOSED
            previous.closed_by = actor
            previous.close_reason = "reassigned"
            previous.save(
                update_fields=["returned_at", "status", "closed_by", "close_reason", "updated_at"]
            )
        assignment = Assignment.objects.create(
            asset=locked,
            custodian=custodian,
            department=department or locked.department,
            location=location or locked.location,
            expected_return_at=expected_return_at,
            notes=notes,
        )
        target = custodian or department or location
        if custodian is not None:
            locked.custodian = custodian
            locked.save(update_fields=["custodian", "updated_at"])
        transition_status(
            actor=actor,
            asset=locked,
            to_code="assigned",
            correlation_id=correlation_id,
            event_type="assigned",
            summary=f"Asset {locked.tag} assigned to {target}.",
            details={"assignment_uuid": str(assignment.uuid)},
        )
        record_audit(
            actor=actor,
            action="asset.assign",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
        if custodian is not None:
            notify(
                recipient=custodian,
                type="assignment.created",
                title=f"Asset assigned: {locked.tag}",
                body=f"{locked.tag} ({locked.name}) was assigned to you.",
                link=f"/assets/{locked.uuid}",
                dedupe_key=f"assignment:{assignment.uuid}",
            )
    return assignment


def return_asset(
    *,
    actor,
    asset: Asset,
    condition=None,
    notes: str = "",
    close_reason: str = "returned",
    correlation_id=None,
) -> Assignment:
    """FR-009: check in an asset, closing its active assignment."""
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        assignment = locked.assignments.filter(returned_at__isnull=True).first()
        if assignment is None:
            raise ApiException(
                409,
                "ASSIGNMENT_CONFLICT",
                "This asset has no active assignment to return.",
            )
        assignment.returned_at = timezone.now()
        assignment.status = Assignment.Status.CLOSED
        assignment.closed_by = actor
        assignment.close_reason = close_reason
        if notes:
            assignment.notes = (assignment.notes + "\n" + notes).strip()
        assignment.save(
            update_fields=[
                "returned_at",
                "status",
                "closed_by",
                "close_reason",
                "notes",
                "updated_at",
            ]
        )
        update_fields = ["custodian", "updated_at"]
        locked.custodian = None
        if condition is not None:
            locked.condition = condition
            update_fields.append("condition")
        locked.save(update_fields=update_fields)
        transition_status(
            actor=actor,
            asset=locked,
            to_code="available",
            correlation_id=correlation_id,
            event_type="returned",
            summary=f"Asset {locked.tag} returned ({close_reason}).",
            details={"assignment_uuid": str(assignment.uuid)},
        )
        record_audit(
            actor=actor,
            action="asset.return",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return assignment


def transfer_asset(
    *,
    actor,
    asset: Asset,
    to_custodian=None,
    to_department=None,
    to_location=None,
    reason: str = "",
    evidence: str = "",
    correlation_id=None,
    skip_approval: bool = False,
):
    """FR-008 step 1: initiate a transfer; the asset goes In Transit.

    Returns a TransferRecord, or a pending ApprovalRequest when the
    in_transit transition rule requires approval (FR-024).
    """
    if not any([to_custodian, to_department, to_location]):
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "Provide a destination custodian, department, or location.",
            field_errors={"to_location": ["A destination is required."]},
        )
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        if locked.transfers.filter(status=TransferRecord.Status.IN_TRANSIT).exists():
            raise ApiException(
                409,
                "TRANSFER_IN_PROGRESS",
                "This asset already has an open transfer. Confirm receipt first.",
            )
        if not skip_approval:
            from apps.approvals.services import maybe_create_approval

            approval = maybe_create_approval(
                actor=actor,
                asset=locked,
                request_type="transfer",
                to_code="in_transit",
                payload={
                    "to_custodian": str(to_custodian.uuid) if to_custodian else None,
                    "to_department": str(to_department.uuid) if to_department else None,
                    "to_location": str(to_location.uuid) if to_location else None,
                    "reason": reason,
                    "evidence": evidence,
                },
                reason=reason,
                correlation_id=correlation_id,
            )
            if approval is not None:
                return approval
        transfer = TransferRecord.objects.create(
            asset=locked,
            from_custodian=locked.custodian,
            from_location=locked.location,
            from_department=locked.department,
            to_custodian=to_custodian,
            to_department=to_department,
            to_location=to_location,
            requester=actor,
            reason=reason,
            evidence=evidence,
        )
        transition_status(
            actor=actor,
            asset=locked,
            to_code="in_transit",
            correlation_id=correlation_id,
            event_type="transfer_initiated",
            summary=f"Asset {locked.tag} transferred (in transit).",
            details={"transfer_uuid": str(transfer.uuid), "reason": reason},
        )
        record_audit(
            actor=actor,
            action="asset.transfer",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return transfer


def confirm_transfer(*, actor, asset: Asset, correlation_id=None) -> TransferRecord:
    """FR-008 step 2: recipient confirmation; destination data is applied and
    custody moves when the transfer names a new custodian."""
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        transfer = locked.transfers.filter(status=TransferRecord.Status.IN_TRANSIT).first()
        if transfer is None:
            raise ApiException(
                409,
                "TRANSFER_NOT_OPEN",
                "This asset has no open transfer to confirm.",
            )
        transfer.status = TransferRecord.Status.RECEIVED
        transfer.confirmed_by = actor
        transfer.confirmed_at = timezone.now()
        transfer.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])
        update_fields = ["updated_at"]
        if transfer.to_location is not None:
            locked.location = transfer.to_location
            update_fields.append("location")
        if transfer.to_department is not None:
            locked.department = transfer.to_department
            update_fields.append("department")
        if transfer.to_custodian is not None:
            locked.custodian = transfer.to_custodian
            update_fields.append("custodian")
        locked.save(update_fields=update_fields)
        if transfer.to_custodian is not None:
            assign_asset(
                actor=actor,
                asset=locked,
                custodian=transfer.to_custodian,
                department=locked.department,
                location=locked.location,
                notes="Custody moved via confirmed transfer.",
                correlation_id=correlation_id,
            )
        else:
            transition_status(
                actor=actor,
                asset=locked,
                to_code="available",
                correlation_id=correlation_id,
                event_type="transfer_received",
                summary=f"Asset {locked.tag} received at destination.",
                details={"transfer_uuid": str(transfer.uuid)},
            )
        record_audit(
            actor=actor,
            action="asset.transfer.confirm",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return transfer


def reserve_asset(
    *,
    actor,
    asset: Asset,
    start_at,
    end_at,
    purpose: str = "",
    notes: str = "",
    correlation_id=None,
) -> Reservation:
    """FR-010: create a reservation; overlapping active reservations conflict."""
    if start_at is None or end_at is None or end_at <= start_at:
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "Reservation end must be after its start.",
            field_errors={"end_at": ["End must be after start."]},
        )
    with transaction.atomic():
        locked = _lock_asset(asset)
        overlap = locked.reservations.filter(
            status__in=Reservation.ACTIVE_STATUSES,
            start_at__lt=end_at,
            end_at__gt=start_at,
        ).first()
        if overlap is not None:
            raise ApiException(
                409,
                "RESERVATION_CONFLICT",
                "An active reservation already overlaps this period.",
                field_errors={"start_at": ["Overlapping reservation exists."]},
            )
        reservation = Reservation.objects.create(
            asset=locked,
            requester=actor,
            start_at=start_at,
            end_at=end_at,
            purpose=purpose,
            notes=notes,
        )
        _lifecycle(
            locked,
            actor,
            "reserved",
            f"Asset {locked.tag} reserved from {start_at.isoformat()} to {end_at.isoformat()}.",
            {"reservation_uuid": str(reservation.uuid)},
            correlation_id,
        )
        record_audit(
            actor=actor,
            action="asset.reserve",
            target=locked,
            after={"reservation_uuid": str(reservation.uuid)},
            correlation_id=correlation_id,
        )
    return reservation


def checkout_reservation(
    *, actor, asset: Asset, reservation_uuid, correlation_id=None
) -> Assignment:
    """FR-010: check out a confirmed reservation to its requester."""
    with transaction.atomic():
        locked = _lock_asset(asset)
        reservation = locked.reservations.filter(
            uuid=reservation_uuid,
            status__in=(Reservation.Status.REQUESTED, Reservation.Status.CONFIRMED),
        ).first()
        if reservation is None:
            raise ApiException(
                409,
                "RESERVATION_CONFLICT",
                "No active reservation with this identifier exists for the asset.",
            )
        if locked.assignments.filter(returned_at__isnull=True).exists():
            raise ApiException(
                409,
                "ASSIGNMENT_CONFLICT",
                "This asset already has an active assignment.",
            )
        reservation.status = Reservation.Status.CHECKED_OUT
        reservation.save(update_fields=["status", "updated_at"])
        assignment = assign_asset(
            actor=actor,
            asset=locked,
            custodian=reservation.requester,
            department=locked.department,
            location=locked.location,
            expected_return_at=reservation.end_at,
            notes=f"Checked out under reservation {reservation.uuid}.",
            correlation_id=correlation_id,
        )
        _lifecycle(
            locked,
            actor,
            "checked_out",
            f"Asset {locked.tag} checked out under reservation.",
            {"reservation_uuid": str(reservation.uuid)},
            correlation_id,
        )
    return assignment


def report_exception(
    *,
    actor,
    asset: Asset,
    report_type: str,
    description: str = "",
    evidence: str = "",
    correlation_id=None,
) -> ExceptionReport:
    """FR-013: report an asset lost/stolen/missing/damaged. The original event
    is preserved forever (BR-003); resolution happens via resolve_exception.
    """
    valid_types = {choice for choice, _ in ExceptionReport.ReportType.choices}
    if report_type not in valid_types:
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "Unknown exception report type.",
            field_errors={"report_type": [f"Must be one of: {', '.join(sorted(valid_types))}."]},
        )
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        report = ExceptionReport.objects.create(
            asset=locked,
            report_type=report_type,
            reporter=actor,
            description=description,
            evidence=evidence,
        )
        if report_type == ExceptionReport.ReportType.DAMAGED:
            damaged = AssetCondition.objects.filter(code="damaged").first()
            if damaged is not None and locked.condition_id != damaged.id:
                locked.condition = damaged
                locked.save(update_fields=["condition", "updated_at"])
            _lifecycle(
                locked,
                actor,
                "reported_damaged",
                f"Asset {locked.tag} reported damaged: {description or 'no details'}.",
                {"report_uuid": str(report.uuid)},
                correlation_id,
            )
        else:
            # Endpoint-level permission governs; employees may report their own
            # assets, so the transition role check is skipped deliberately.
            transition_status(
                actor=actor,
                asset=locked,
                to_code=report_type,
                correlation_id=correlation_id,
                event_type=f"reported_{report_type}",
                summary=f"Asset {locked.tag} reported {report_type}.",
                details={"report_uuid": str(report.uuid)},
                check_role=False,
            )
        record_audit(
            actor=actor,
            action="asset.exception.report",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
        notify_roles(
            roles={"system_admin", "asset_manager"},
            type="exception.reported",
            title=f"Exception reported: {locked.tag} ({report_type})",
            body=description or f"Asset {locked.tag} was reported {report_type}.",
            link=f"/assets/{locked.uuid}",
            dedupe_key=f"exception:{report.uuid}",
        )
    return report


def resolve_exception(
    *, actor, asset: Asset, resolution: str = "", correlation_id=None
) -> ExceptionReport:
    """FR-013: resolve the asset's open exception report; the original report
    remains on record (BR-003)."""
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        report = locked.exception_reports.filter(status=ExceptionReport.Status.OPEN).first()
        if report is None:
            raise ApiException(
                409,
                "EXCEPTION_NOT_OPEN",
                "This asset has no open exception report.",
            )
        report.status = ExceptionReport.Status.RESOLVED
        report.resolution = resolution
        report.resolved_by = actor
        report.resolved_at = timezone.now()
        report.save(
            update_fields=["status", "resolution", "resolved_by", "resolved_at", "updated_at"]
        )
        if report.report_type != ExceptionReport.ReportType.DAMAGED:
            transition_status(
                actor=actor,
                asset=locked,
                to_code="available",
                correlation_id=correlation_id,
                event_type="exception_resolved",
                summary=f"Asset {locked.tag} exception resolved; back to available.",
                details={"report_uuid": str(report.uuid)},
                check_role=False,
            )
        record_audit(
            actor=actor,
            action="asset.exception.resolve",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return report


# -- Retirement / disposal / reopen (FR-014; Cycle 3) ------------------------


def disposal_blockers(asset: Asset) -> list[str]:
    """BR-006: operational records that block disposal."""
    blockers: list[str] = []
    if asset.assignments.filter(returned_at__isnull=True).exists():
        blockers.append("open_assignment")
    if asset.transfers.filter(status=TransferRecord.Status.IN_TRANSIT).exists():
        blockers.append("transfer_in_transit")
    if asset.maintenance_records.filter(status="open").exists():
        blockers.append("open_maintenance")
    if asset.exception_reports.filter(status=ExceptionReport.Status.OPEN).exists():
        blockers.append("open_exception_report")
    return blockers


def retire_asset(*, actor, asset: Asset, reason: str = "", correlation_id=None) -> Asset:
    """FR-014: retire an asset (end of useful life, pre-disposal)."""
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        transition_status(
            actor=actor,
            asset=locked,
            to_code="retired",
            correlation_id=correlation_id,
            event_type="retired",
            summary=f"Asset {locked.tag} retired.",
            details={"reason": reason},
        )
        locked.retirement_date = timezone.now().date()
        locked.save(update_fields=["retirement_date", "updated_at"])
        record_audit(
            actor=actor,
            action="asset.retire",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return locked


def execute_disposal(
    *, actor, asset: Asset, method: str = "", reason: str = "", correlation_id=None
) -> Asset:
    """Apply disposal to an asset (blockers + approval already settled by the
    caller). Runs its own atomic block + row lock so it is safe standalone."""
    with transaction.atomic():
        locked = _lock_asset(asset)
        before = snapshot(locked)
        transition_status(
            actor=actor,
            asset=locked,
            to_code="disposed",
            correlation_id=correlation_id,
            event_type="disposed",
            summary=f"Asset {locked.tag} disposed ({method or 'no method recorded'}).",
            details={"method": method, "reason": reason},
        )
        today = timezone.now().date()
        locked.disposal_date = today
        locked.disposal_method = method
        locked.disposal_reason = reason
        if locked.retirement_date is None:
            locked.retirement_date = today
        locked.save(
            update_fields=[
                "disposal_date",
                "disposal_method",
                "disposal_reason",
                "retirement_date",
                "updated_at",
            ]
        )
        record_audit(
            actor=actor,
            action="asset.dispose",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return locked


def dispose_asset(
    *,
    actor,
    asset: Asset,
    method: str = "",
    reason: str = "",
    force: bool = False,
    correlation_id=None,
):
    """FR-014: dispose of an asset.

    BR-006 blockers (open assignment/transfer/maintenance/exception) reject
    with 409 DISPOSAL_BLOCKED unless ``force`` is passed by a manager/admin.
    Returns the disposed Asset, or a pending ApprovalRequest when the
    disposed transition rule requires approval (FR-024).
    """
    with transaction.atomic():
        locked = _lock_asset(asset)
        blockers = disposal_blockers(locked)
        if blockers and not (force and actor.role in DISPOSAL_OVERRIDE_ROLES):
            raise ApiException(
                409,
                "DISPOSAL_BLOCKED",
                "Disposal is blocked by open operational records.",
                field_errors={"blockers": blockers},
            )
        from apps.approvals.services import maybe_create_approval

        approval = maybe_create_approval(
            actor=actor,
            asset=locked,
            request_type="disposal",
            to_code="disposed",
            payload={"method": method, "reason": reason, "force": force},
            reason=reason,
            correlation_id=correlation_id,
        )
        if approval is not None:
            return approval
    return execute_disposal(
        actor=actor, asset=locked, method=method, reason=reason, correlation_id=correlation_id
    )


def reopen_asset(*, actor, asset: Asset, justification: str = "", correlation_id=None) -> Asset:
    """FR-014: reopen a disposed asset. Admin-only (endpoint); the recorded
    justification is mandatory and preserved in lifecycle + audit history.
    Disposal data is retained as history (BR-003)."""
    if not justification.strip():
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "A recorded justification is required to reopen a disposed asset.",
            field_errors={"justification": ["This field is required."]},
        )
    with transaction.atomic():
        locked = _lock_asset(asset)
        if locked.status.code != "disposed":
            raise ApiException(
                409,
                "STATUS_TRANSITION_INVALID",
                "Only disposed assets can be reopened.",
            )
        target = AssetStatus.objects.filter(code="retired").first()
        if target is None:
            raise ApiException(
                409,
                "STATUS_TRANSITION_INVALID",
                "The 'retired' status is not configured.",
            )
        before = snapshot(locked)
        # Deliberate, admin-only bypass of the terminal-status guard (FR-014).
        locked.status = target
        locked.save(update_fields=["status", "updated_at"])
        _lifecycle(
            locked,
            actor,
            "reopened",
            f"Disposed asset {locked.tag} reopened: {justification.strip()}",
            {"justification": justification.strip()},
            correlation_id,
        )
        record_audit(
            actor=actor,
            action="asset.reopen",
            target=locked,
            before=before,
            after=snapshot(locked),
            correlation_id=correlation_id,
        )
    return locked
