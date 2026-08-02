import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def test_hash_chain_links_events(make_user, reference):
    from apps.assets.models import Asset
    from apps.audit.models import AuditEvent
    from apps.audit.services import record_audit, verify_chain

    actor = make_user("aud-chain", "system_admin")
    asset = Asset.objects.create(
        tag="AST-555555",
        name="Chain test",
        category=reference.category,
        status=reference.in_stock,
    )
    record_audit(actor=actor, action="asset.create", target=asset, after={"tag": asset.tag})
    record_audit(
        actor=actor,
        action="asset.update",
        target=asset,
        before={"name": "Chain test"},
        after={"name": "Chain test 2"},
    )
    events = list(AuditEvent.objects.order_by("id"))
    assert len(events) == 2
    assert events[1].prev_hash == events[0].record_hash
    assert verify_chain() is True


def test_tampering_is_detected(make_user, reference):
    from apps.assets.models import Asset
    from apps.audit.models import AuditEvent
    from apps.audit.services import record_audit, verify_chain

    actor = make_user("aud-tamper", "system_admin")
    asset = Asset.objects.create(
        tag="AST-666666",
        name="Tamper test",
        category=reference.category,
        status=reference.in_stock,
    )
    record_audit(actor=actor, action="asset.create", target=asset)
    event = AuditEvent.objects.order_by("id").first()
    # Simulate an out-of-band tamper (bypassing app code).
    AuditEvent.objects.filter(pk=event.pk).update(after={"tag": "FORGED"})
    assert verify_chain() is False
