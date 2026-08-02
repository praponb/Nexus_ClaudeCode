"""Stocktake application services (FR-022).

Sessions: draft -> open -> reconciling -> closed. Observations are classified
on entry (found / unexpected / duplicate / moved / condition_mismatch).
Reconciliation applies reviewed master-data updates (location/condition)
atomically; closing requires the reconciling state and yields the final
variance report.
"""

from django.db import transaction
from django.utils import timezone

from apps.assets.models import Asset, LifecycleEvent
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.stocktakes.models import StocktakeObservation, StocktakeSession

COUNTED_OUTCOMES = (
    StocktakeObservation.Outcome.FOUND,
    StocktakeObservation.Outcome.MOVED,
    StocktakeObservation.Outcome.CONDITION_MISMATCH,
    StocktakeObservation.Outcome.DUPLICATE,
)


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


def create_session(
    *,
    actor,
    name: str,
    locations=None,
    operators=None,
    start_at=None,
    due_at=None,
    instructions: str = "",
    correlation_id=None,
) -> StocktakeSession:
    session = StocktakeSession.objects.create(
        name=name,
        start_at=start_at,
        due_at=due_at,
        instructions=instructions,
        created_by=actor,
    )
    if locations:
        session.locations.set(locations)
    if operators:
        session.operators.set(operators)
    record_audit(
        actor=actor,
        action="stocktake.create",
        target=session,
        after={"name": name, "status": session.status},
        correlation_id=correlation_id,
    )
    return session


def start_session(*, actor, session: StocktakeSession, correlation_id=None) -> StocktakeSession:
    with transaction.atomic():
        locked = StocktakeSession.objects.select_for_update().get(pk=session.pk)
        if locked.status != StocktakeSession.Status.DRAFT:
            raise ApiException(
                409, "STOCKTAKE_STATE_INVALID", "Only a draft session can be started."
            )
        locked.status = StocktakeSession.Status.OPEN
        locked.snapshot_at = timezone.now()
        locked.start_at = locked.start_at or locked.snapshot_at
        locked.save(update_fields=["status", "snapshot_at", "start_at", "updated_at"])
        record_audit(
            actor=actor,
            action="stocktake.start",
            target=locked,
            before={"status": "draft"},
            after={"status": locked.status},
            correlation_id=correlation_id,
        )
    return locked


def record_observation(
    *,
    actor,
    session: StocktakeSession,
    tag_scanned: str,
    location=None,
    condition=None,
    note: str = "",
    correlation_id=None,
) -> StocktakeObservation:
    tag_scanned = (tag_scanned or "").strip()
    if not tag_scanned:
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "A scanned or manually entered tag is required.",
            field_errors={"tag_scanned": ["This field is required."]},
        )
    with transaction.atomic():
        locked = StocktakeSession.objects.select_for_update().get(pk=session.pk)
        if locked.status != StocktakeSession.Status.OPEN:
            raise ApiException(
                409,
                "STOCKTAKE_STATE_INVALID",
                "Observations can only be recorded while the session is open.",
            )
        asset = Asset.objects.filter(tag__iexact=tag_scanned).first()
        outcome = StocktakeObservation.Outcome.FOUND
        if asset is None:
            # Unknown code: recorded but non-destructive (FR-017/FR-022).
            outcome = StocktakeObservation.Outcome.UNEXPECTED
        elif locked.observations.filter(asset=asset, outcome__in=COUNTED_OUTCOMES).exists():
            outcome = StocktakeObservation.Outcome.DUPLICATE
        elif location is not None and asset.location_id != location.id:
            outcome = StocktakeObservation.Outcome.MOVED
        elif condition is not None and asset.condition_id != condition.id:
            outcome = StocktakeObservation.Outcome.CONDITION_MISMATCH
        observation = StocktakeObservation.objects.create(
            session=locked,
            asset=asset,
            tag_scanned=tag_scanned,
            operator=actor,
            location=location,
            condition=condition,
            note=note,
            outcome=outcome,
        )
        if asset is not None:
            _lifecycle(
                asset,
                actor,
                "stocktake_observed",
                f"Observed in stocktake '{locked.name}' (outcome: {outcome}).",
                {"session_uuid": str(locked.uuid), "outcome": outcome},
                correlation_id,
            )
    return observation


def expected_assets(session: StocktakeSession):
    """Assets expected in this session's scope (locations at snapshot time;
    Cycle-2 simplification: current locations)."""
    location_ids = session.locations.values_list("id", flat=True)
    queryset = Asset.objects.filter(record_status="active")
    if location_ids:
        queryset = queryset.filter(location_id__in=location_ids)
    return queryset


def compute_variance(session: StocktakeSession) -> dict:
    counted_ids = set(
        session.observations.filter(outcome__in=COUNTED_OUTCOMES, asset__isnull=False).values_list(
            "asset_id", flat=True
        )
    )
    expected = list(expected_assets(session).select_related("status", "location"))
    not_found = [asset for asset in expected if asset.id not in counted_ids]
    observations = session.observations.select_related("asset", "location", "condition")
    return {
        "session_uuid": str(session.uuid),
        "status": session.status,
        "expected_count": len(expected),
        "found_count": len(counted_ids),
        "not_found": [
            {"uuid": str(asset.uuid), "tag": asset.tag, "name": asset.name} for asset in not_found
        ],
        "unexpected": [
            {"tag_scanned": obs.tag_scanned, "observed_at": obs.observed_at}
            for obs in observations
            if obs.outcome == StocktakeObservation.Outcome.UNEXPECTED
        ],
        "duplicates": [
            {"tag_scanned": obs.tag_scanned, "observed_at": obs.observed_at}
            for obs in observations
            if obs.outcome == StocktakeObservation.Outcome.DUPLICATE
        ],
        "moved": [
            {
                "tag": obs.asset.tag if obs.asset else obs.tag_scanned,
                "observed_location": obs.location.name if obs.location else None,
            }
            for obs in observations
            if obs.outcome == StocktakeObservation.Outcome.MOVED
        ],
        "condition_mismatches": [
            {
                "tag": obs.asset.tag if obs.asset else obs.tag_scanned,
                "observed_condition": obs.condition.label if obs.condition else None,
            }
            for obs in observations
            if obs.outcome == StocktakeObservation.Outcome.CONDITION_MISMATCH
        ],
    }


def reconcile_session(*, actor, session: StocktakeSession, correlation_id=None) -> StocktakeSession:
    """Review step: applies location/condition master-data updates from
    observations (audited), then marks the session reconciling."""
    with transaction.atomic():
        locked = StocktakeSession.objects.select_for_update().get(pk=session.pk)
        if locked.status != StocktakeSession.Status.OPEN:
            raise ApiException(
                409, "STOCKTAKE_STATE_INVALID", "Only an open session can be reconciled."
            )
        moved = locked.observations.filter(
            outcome=StocktakeObservation.Outcome.MOVED, asset__isnull=False
        ).select_related("asset", "location")
        for observation in moved:
            if observation.asset_id is None or observation.location is None:
                continue
            asset = Asset.objects.select_for_update().get(pk=observation.asset_id)
            asset.location = observation.location
            asset.save(update_fields=["location", "updated_at"])
            _lifecycle(
                asset,
                actor,
                "stocktake_adjustment",
                f"Location updated from stocktake '{locked.name}'.",
                {"session_uuid": str(locked.uuid), "new_location": observation.location.name},
                correlation_id,
            )
        mismatched = locked.observations.filter(
            outcome=StocktakeObservation.Outcome.CONDITION_MISMATCH, asset__isnull=False
        ).select_related("asset", "condition")
        for observation in mismatched:
            if observation.asset_id is None or observation.condition is None:
                continue
            asset = Asset.objects.select_for_update().get(pk=observation.asset_id)
            asset.condition = observation.condition
            asset.save(update_fields=["condition", "updated_at"])
            _lifecycle(
                asset,
                actor,
                "stocktake_adjustment",
                f"Condition updated from stocktake '{locked.name}'.",
                {"session_uuid": str(locked.uuid), "new_condition": observation.condition.label},
                correlation_id,
            )
        locked.status = StocktakeSession.Status.RECONCILING
        locked.save(update_fields=["status", "updated_at"])
        record_audit(
            actor=actor,
            action="stocktake.reconcile",
            target=locked,
            before={"status": "open"},
            after={"status": locked.status},
            correlation_id=correlation_id,
        )
    return locked


def close_session(*, actor, session: StocktakeSession, correlation_id=None) -> StocktakeSession:
    with transaction.atomic():
        locked = StocktakeSession.objects.select_for_update().get(pk=session.pk)
        if locked.status != StocktakeSession.Status.RECONCILING:
            raise ApiException(
                409,
                "STOCKTAKE_STATE_INVALID",
                "A session must be reconciled before it can be closed.",
            )
        variance = compute_variance(locked)
        locked.status = StocktakeSession.Status.CLOSED
        locked.save(update_fields=["status", "updated_at"])
        record_audit(
            actor=actor,
            action="stocktake.close",
            target=locked,
            before={"status": "reconciling"},
            after={
                "status": locked.status,
                "expected_count": variance["expected_count"],
                "found_count": variance["found_count"],
            },
            correlation_id=correlation_id,
        )
    return locked
