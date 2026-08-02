"""Approval workflow services (FR-024).

Gating is configured per transition rule (StatusTransitionRule.requires_approval)
and can be disabled deployment-wide via APPROVALS_ENABLED=false (A-05). Decisions
are immutable, audited, and separation-of-duties aware (requester != approver
when APPROVAL_SEPARATION_OF_DUTIES=true, the default).
"""

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest
from apps.assets.models import LifecycleEvent
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.notifications.services import notify, notify_roles
from apps.reference_data.models import Department, Location, StatusTransitionRule

APPROVER_ROLES = {"system_admin", "asset_manager", "department_manager"}


def approvals_enabled() -> bool:
    return getattr(settings, "APPROVALS_ENABLED", True)


def can_approve(user) -> bool:
    return getattr(user, "role", "") in APPROVER_ROLES


def maybe_create_approval(
    *,
    actor,
    asset,
    request_type: str,
    to_code: str,
    payload: dict,
    reason: str = "",
    correlation_id=None,
) -> ApprovalRequest | None:
    """Return a pending ApprovalRequest when the transition rule for
    ``asset.status -> to_code`` requires approval; otherwise None.

    The caller must hold a row lock on ``asset`` inside a transaction.
    """
    if not approvals_enabled():
        return None
    rule = StatusTransitionRule.objects.filter(
        from_status=asset.status, to_status__code=to_code
    ).first()
    if rule is None or not rule.requires_approval:
        return None
    request = ApprovalRequest.objects.create(
        request_type=request_type,
        requester=actor,
        asset=asset,
        to_code=to_code,
        payload=payload,
        reason=reason,
    )
    LifecycleEvent.objects.create(
        asset=asset,
        event_type="approval_requested",
        actor=actor,
        occurred_at=timezone.now(),
        summary=f"{request.get_request_type_display()} of {asset.tag} requires approval.",
        details={"approval_uuid": str(request.uuid), "to_code": to_code},
        correlation_id=correlation_id,
    )
    record_audit(
        actor=actor,
        action="approval.request",
        target=asset,
        after={"approval_uuid": str(request.uuid), "request_type": request_type},
        correlation_id=correlation_id,
    )
    notify_roles(
        roles=APPROVER_ROLES,
        type="approval.requested",
        title=f"Approval requested: {request.get_request_type_display()} of {asset.tag}",
        body=reason or f"{request.get_request_type_display()} of {asset.tag} awaits a decision.",
        link="/approvals",
        dedupe_key=f"approval:{request.uuid}",
    )
    return request


def _resolve(model, raw_uuid):
    if not raw_uuid:
        return None
    return model.objects.filter(uuid=raw_uuid).first()


def _execute_approved(request: ApprovalRequest, *, actor, correlation_id=None) -> None:
    """Run the held action for an approved request. Caller holds locks."""
    from apps.assignments import services as workflow

    payload = dict(request.payload or {})
    if request.request_type == ApprovalRequest.RequestType.DISPOSAL:
        blockers = workflow.disposal_blockers(request.asset)
        if blockers and not payload.get("force"):
            raise ApiException(
                409,
                "DISPOSAL_BLOCKED",
                "Disposal is blocked by open operational records.",
                field_errors={"blockers": blockers},
            )
        workflow.execute_disposal(
            actor=actor,
            asset=request.asset,
            method=payload.get("method", ""),
            reason=payload.get("reason", ""),
            correlation_id=correlation_id,
        )
    elif request.request_type == ApprovalRequest.RequestType.TRANSFER:
        workflow.transfer_asset(
            actor=actor,
            asset=request.asset,
            to_custodian=_resolve(User, payload.get("to_custodian")),
            to_department=_resolve(Department, payload.get("to_department")),
            to_location=_resolve(Location, payload.get("to_location")),
            reason=payload.get("reason", ""),
            evidence=payload.get("evidence", ""),
            correlation_id=correlation_id,
            skip_approval=True,
        )
    # write_off / sensitive_update: no held action in v1; the decision record
    # itself is the controlled artifact.


def decide(
    *,
    request: ApprovalRequest,
    actor,
    decision: str,
    comments: str = "",
    correlation_id=None,
) -> ApprovalRequest:
    """Approve / reject / return a pending request. Immutable after decision."""
    if not can_approve(actor):
        raise ApiException(
            403,
            "PERMISSION_DENIED",
            "Only department managers, asset managers, or administrators can decide approvals.",
        )
    if decision not in {
        ApprovalRequest.Status.APPROVED,
        ApprovalRequest.Status.REJECTED,
        ApprovalRequest.Status.RETURNED,
    }:
        raise ApiException(400, "VALIDATION_FAILED", "Unknown approval decision.")
    with transaction.atomic():
        locked = ApprovalRequest.objects.select_for_update().get(pk=request.pk)
        if locked.status != ApprovalRequest.Status.PENDING:
            raise ApiException(
                409,
                "APPROVAL_ALREADY_DECIDED",
                "This approval request has already been decided.",
            )
        if (
            getattr(settings, "APPROVAL_SEPARATION_OF_DUTIES", True)
            and locked.requester_id is not None
            and locked.requester_id == actor.id
        ):
            raise ApiException(
                409,
                "SEPARATION_OF_DUTIES",
                "The requester cannot decide their own approval request.",
            )
        locked.status = decision
        locked.approver = actor
        locked.decided_at = timezone.now()
        locked.comments = comments
        locked.save(update_fields=["status", "approver", "decided_at", "comments", "updated_at"])
        LifecycleEvent.objects.create(
            asset=locked.asset,
            event_type=f"approval_{decision}",
            actor=actor,
            occurred_at=timezone.now(),
            summary=(
                f"{locked.get_request_type_display()} approval for {locked.asset.tag} {decision}."
            ),
            details={"approval_uuid": str(locked.uuid), "comments": comments},
            correlation_id=correlation_id,
        )
        record_audit(
            actor=actor,
            action=f"approval.{decision}",
            target=locked.asset,
            after={"approval_uuid": str(locked.uuid), "decision": decision},
            correlation_id=correlation_id,
        )
        if decision == ApprovalRequest.Status.APPROVED:
            _execute_approved(locked, actor=actor, correlation_id=correlation_id)
        if locked.requester is not None:
            notify(
                recipient=locked.requester,
                type="approval.decided",
                title=(
                    f"Approval {decision}: "
                    f"{locked.get_request_type_display()} of {locked.asset.tag}"
                ),
                body=comments
                or f"Your {locked.get_request_type_display().lower()} request was {decision}.",
                link="/approvals",
                dedupe_key=f"approval-decided:{locked.uuid}",
            )
    return locked
