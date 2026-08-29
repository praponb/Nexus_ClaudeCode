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


def test_report_names_a_deleted_actor_as_the_cause(make_user):
    """A deleted actor breaks the row hash while leaving the links intact.

    That combination is the whole difficulty of SESSION-2026-08-29-ISSUES 2.2:
    ``verify_chain()`` says False and nothing says why, so an ordinary user
    deletion is indistinguishable from tampering. The report has to tell them
    apart, and it has to recover the deleted actor's UUID from ``target_uuid``,
    because the users table no longer holds it.
    """
    from io import StringIO

    from django.core.management import call_command

    from apps.audit.services import record_audit, verify_chain

    actor = make_user("aud-vanishing", "system_admin")
    record_audit(actor=actor, action="auth.login", target=actor, outcome="success")
    record_audit(actor=actor, action="auth.logout", target=actor, outcome="success")
    assert verify_chain() is True

    actor.delete()
    assert verify_chain() is False

    out = StringIO()
    call_command("audit_chain_report", stdout=out)
    report = out.getvalue()

    assert "Chain links: INTACT" in report
    assert "2 record(s) disagree with their own hash" in report
    assert "deleted-user<" in report
    assert "2 explained, 0 unexplained" in report
    assert "reseal_chain() was NOT run" in report


def test_report_is_quiet_on_a_healthy_chain(make_user, reference):
    from io import StringIO

    from django.core.management import call_command

    from apps.assets.models import Asset
    from apps.audit.services import record_audit

    actor = make_user("aud-healthy", "system_admin")
    asset = Asset.objects.create(
        tag="AST-777777",
        name="Healthy chain",
        category=reference.category,
        status=reference.in_stock,
    )
    record_audit(actor=actor, action="asset.create", target=asset, after={"tag": asset.tag})

    out = StringIO()
    call_command("audit_chain_report", stdout=out)
    report = out.getvalue()

    assert "Chain links: INTACT" in report
    assert "Every record hash recomputes" in report
