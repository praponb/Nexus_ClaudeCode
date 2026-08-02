import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def test_assignment_single_active_per_asset_constraint(make_user, reference):
    """BR-002: partial unique constraint allows exactly one active assignment."""
    from django.db import IntegrityError, transaction

    from apps.assets.models import Asset
    from apps.assignments.models import Assignment

    custodian = make_user("emp-b002", "employee")
    asset = Asset.objects.create(
        tag="AST-810001",
        name="Constraint laptop",
        category=reference.category,
        status=reference.in_stock,
    )
    Assignment.objects.create(asset=asset, custodian=custodian)
    with pytest.raises(IntegrityError), transaction.atomic():
        Assignment.objects.create(asset=asset, custodian=custodian)

    # Closing the first assignment permits a new active one.
    first = Assignment.objects.get(asset=asset, returned_at__isnull=True)
    from django.utils import timezone

    first.returned_at = timezone.now()
    first.status = "closed"
    first.save(update_fields=["returned_at", "status", "updated_at"])
    Assignment.objects.create(asset=asset, custodian=custodian)
    assert Assignment.objects.filter(asset=asset).count() == 2


def test_asset_tag_unique_at_database_level(reference):
    """BR-001: tag uniqueness is a hard DB constraint, not only service logic."""
    from django.db import IntegrityError, transaction

    from apps.assets.models import Asset

    Asset.objects.create(
        tag="AST-810002", name="First", category=reference.category, status=reference.in_stock
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Asset.objects.create(
            tag="AST-810002",
            name="Second",
            category=reference.category,
            status=reference.in_stock,
        )


def test_warranty_date_check_constraint(reference):
    """BR-005: warranty_end must be on/after warranty_start at the DB level."""
    import datetime

    from django.db import IntegrityError, transaction

    from apps.assets.models import Asset

    with pytest.raises(IntegrityError), transaction.atomic():
        Asset.objects.create(
            tag="AST-810003",
            name="Bad warranty",
            category=reference.category,
            status=reference.in_stock,
            warranty_start=datetime.date(2024, 6, 1),
            warranty_end=datetime.date(2024, 1, 1),
        )


def test_tag_sequence_generates_unique_incrementing_tags():
    from apps.assets.services import generate_next_tag

    first = generate_next_tag("TST")
    second = generate_next_tag("TST")
    assert first != second
    assert first == "TST-000001"
    assert second == "TST-000002"


def test_audit_hash_chain_verifies_and_detects_tampering(make_user):
    from apps.audit.models import AuditEvent
    from apps.audit.services import record_audit, verify_chain

    user = make_user("aud-chain2", "auditor")
    record_audit(actor=user, action="test.event.one", after={"n": 1})
    record_audit(actor=user, action="test.event.two", after={"n": 2})
    assert verify_chain() is True

    events = list(AuditEvent.objects.order_by("id"))
    assert events[0].prev_hash == ""
    assert events[1].prev_hash == events[0].record_hash
    assert all(len(event.record_hash) == 64 for event in events)

    # Simulate tampering at the database level (bypasses the app, which never
    # updates audit rows); verification must fail.
    AuditEvent.objects.filter(pk=events[0].pk).update(action="tampered.action")
    assert verify_chain() is False


def test_audit_records_create_and_update_completely(api_client, authed, make_user, reference):
    """FR-025 completeness: create + update emit audit events with before/after."""
    from apps.audit.models import AuditEvent

    operator = make_user("op-auditfull", "operator", scope_department=reference.department)
    client = authed(operator)
    response = client.post(
        "/api/v1/assets/",
        {
            "name": "Audit laptop",
            "category": str(reference.category.uuid),
            "status": str(reference.in_stock.uuid),
            "condition": str(reference.condition.uuid),
            "department": str(reference.department.uuid),
            "location": str(reference.location.uuid),
            "acquisition_type": "purchased",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    asset = response.json()["asset"]

    create_event = AuditEvent.objects.get(action="asset.create", target_uuid=asset["uuid"])
    assert create_event.before is None
    assert create_event.after["name"] == "Audit laptop"
    assert create_event.outcome == "success"
    assert create_event.actor == operator
    assert create_event.record_hash

    response = client.patch(
        f"/api/v1/assets/{asset['uuid']}/",
        {"name": "Audit laptop renamed", "version": asset["version"]},
        format="json",
    )
    assert response.status_code == 200, response.json()
    update_event = AuditEvent.objects.get(action="asset.update", target_uuid=asset["uuid"])
    assert update_event.before["name"] == "Audit laptop"
    assert update_event.after["name"] == "Audit laptop renamed"
    assert update_event.correlation_id is not None
