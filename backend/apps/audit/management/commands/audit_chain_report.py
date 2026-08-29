"""Read-only forensics on the audit hash chain (SESSION-2026-08-29-ISSUES section 2.2).

``verify_chain()`` answers only yes/no. It does not say which rows disagree, nor
why -- so a real chain failure and a bookkeeping artifact look identical. This
command answers the "why": it separates a broken *link* (``prev_hash`` pointing
somewhere other than its predecessor, which is what truncation or splicing looks
like) from a row that merely disagrees with its own hash, and for each of the
latter it replays the payload with fields substituted until it finds the
substitution that reproduces the **stored** hash. That names the cause instead
of leaving it to inference.

Strictly read-only. It deliberately never calls ``reseal_chain()``: resealing
recomputes every hash from whatever is currently stored, so the check would pass
and the evidence needed to explain the discrepancy would be gone.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.audit.models import AuditEvent
from apps.audit.services import _compute_hash, _payload_for


def actor_uuid_pool() -> dict[str, str]:
    """Every user UUID that could have been an actor, as ``{uuid: label}``.

    The users table alone is not enough. ``AuditEvent.actor`` is
    ``on_delete=SET_NULL``, so the interesting case -- a deleted user -- is
    precisely the one whose UUID the table no longer holds. Auth events record
    the same user as their target, and ``target_uuid`` is a plain UUIDField that
    no cascade touches, so a deleted actor's UUID survives there.
    """
    pool = {
        str(uuid): username
        for username, uuid in get_user_model().objects.values_list("username", "uuid")
    }
    user_label = get_user_model()._meta.label_lower
    targets = (
        AuditEvent.objects.filter(target_type=user_label)
        .exclude(target_uuid=None)
        .values_list("target_uuid", flat=True)
        .distinct()
    )
    for target_uuid in targets:
        pool.setdefault(str(target_uuid), f"deleted-user<{target_uuid}>")
    return pool


def _created_at_variants(payload: dict) -> list[tuple[str, str]]:
    """Renderings of ``created_at`` other than the one ``_payload_for`` produces.

    A hash computed at write time under different settings (notably ``USE_TZ``)
    or against a coarser column would have serialized the same instant
    differently. Each variant is labelled so the report says which one hit.
    """
    iso = payload["created_at"]
    variants = [
        ("created_at=Z-suffix", iso.replace("+00:00", "Z")),
        ("created_at=no-offset", iso.replace("+00:00", "")),
        ("created_at=space-separated", iso.replace("T", " ")),
    ]
    if "." in iso:
        head, _, tail = iso.partition(".")
        offset = tail[tail.find("+") :] if "+" in tail else ""
        variants.append(("created_at=second-precision", head + offset))
        variants.append(("created_at=microseconds-zeroed", f"{head}.000000{offset}"))
    return variants


def explain(event: AuditEvent, actor_pool: dict[str, str]) -> str | None:
    """Label the substitution that reproduces the stored hash, or None if none does."""
    stored = event.record_hash
    base = _payload_for(event)

    # The actor FK is on_delete=SET_NULL, so deleting a user silently rewrites
    # the payload of every event that user ever caused while leaving the chain
    # links untouched -- exactly the reported symptom. Tested first.
    actor_candidates: list[tuple[str, str | None]] = [("actor=None", None)]
    actor_candidates += [
        (f"actor={label}", uuid) for uuid, label in sorted(actor_pool.items(), key=lambda kv: kv[1])
    ]

    for actor_label, actor_value in actor_candidates:
        payload = dict(base)
        payload["actor"] = actor_value
        if payload["actor"] != base["actor"] and _compute_hash(event.prev_hash, payload) == stored:
            return actor_label
        for time_label, rendered in _created_at_variants(base):
            probe = dict(payload)
            probe["created_at"] = rendered
            if _compute_hash(event.prev_hash, probe) == stored:
                if payload["actor"] == base["actor"]:
                    return time_label
                return f"{actor_label} + {time_label}"

    for field, replacement, label in (
        ("target_uuid", None, "target_uuid=None"),
        ("before", None, "before=None"),
        ("before", {}, "before={}"),
        ("after", None, "after=None"),
        ("after", {}, "after={}"),
        ("outcome", "success", "outcome=success"),
    ):
        payload = dict(base)
        payload[field] = replacement
        if _compute_hash(event.prev_hash, payload) == stored:
            return label
    return None


class Command(BaseCommand):
    help = "Report which audit events fail hash verification, and why. Never writes."

    def handle(self, *args, **options) -> None:
        events = list(AuditEvent.objects.order_by("id"))
        if not events:
            self.stdout.write("No audit events recorded.")
            return

        actor_pool = actor_uuid_pool()

        broken_links: list[AuditEvent] = []
        bad_hashes: list[AuditEvent] = []
        prev_hash = ""
        for event in events:
            if event.prev_hash != prev_hash:
                broken_links.append(event)
            # Deliberately hashed against the row's OWN prev_hash, not the running
            # one: otherwise a single upstream break makes every later row look
            # tampered with and the report says nothing useful.
            if event.record_hash != _compute_hash(event.prev_hash, _payload_for(event)):
                bad_hashes.append(event)
            prev_hash = event.record_hash

        self.stdout.write(
            f"{len(events)} events (ids {events[0].id}-{events[-1].id}); "
            f"{len(actor_pool)} candidate actor UUIDs."
        )
        link_state = "INTACT" if not broken_links else f"{len(broken_links)} BROKEN"
        self.stdout.write(f"Chain links: {link_state}")
        for event in broken_links:
            self.stdout.write(f"  id={event.id} prev_hash does not match its predecessor")
        if broken_links:
            self.stdout.write(
                "  A broken link is what truncation or splicing looks like. "
                "Investigate that before anything else."
            )

        if not bad_hashes:
            self.stdout.write("Every record hash recomputes. Chain verifies.")
            return

        self.stdout.write(f"\n{len(bad_hashes)} record(s) disagree with their own hash:\n")
        header = f"{'id':>6}  {'action':<20} {'outcome':<8} {'actor_id':>8}  created_at"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        unexplained = 0
        for event in bad_hashes:
            self.stdout.write(
                f"{event.id:>6}  {event.action:<20} {event.outcome:<8} "
                f"{str(event.actor_id or '-'):>8}  {event.created_at.isoformat()}"
            )
            cause = explain(event, actor_pool)
            if cause is None:
                unexplained += 1
                self.stdout.write("        -> UNEXPLAINED by any tested substitution")
            else:
                self.stdout.write(f"        -> stored hash reproduces with {cause}")

        self.stdout.write(
            f"\n{len(bad_hashes) - unexplained} explained, {unexplained} unexplained."
        )
        self.stdout.write("No data was modified. reseal_chain() was NOT run.")
