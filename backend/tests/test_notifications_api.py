"""In-app notifications, preferences, dedupe, and reminder jobs (FR-023)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from datetime import timedelta  # noqa: E402

from django.utils import timezone  # noqa: E402

pytestmark = pytest.mark.django_db


def _operator(make_user, reference, username):
    return make_user(username, "operator", scope_department=reference.department)


def test_assignment_notifies_custodian(api_client, make_user, make_asset, workflow_reference):
    from apps.notifications.models import Notification

    operator = _operator(make_user, workflow_reference, "nt-operator")
    custodian = make_user("nt-custodian", "employee")
    asset = make_asset("NT-001")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )
    notification = Notification.objects.get(recipient=custodian, type="assignment.created")
    assert "/assets/" in notification.link
    assert notification.read_at is None


def test_notification_center_own_only_and_mark_read(
    api_client, make_user, make_asset, workflow_reference
):
    operator = _operator(make_user, workflow_reference, "nt-operator-2")
    custodian = make_user("nt-custodian-2", "employee")
    other = make_user("nt-other", "employee")
    asset = make_asset("NT-002")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )

    api_client.force_authenticate(custodian)
    listed = api_client.get("/api/v1/notifications/")
    assert listed.status_code == 200
    rows = listed.json()["results"]
    assert len(rows) == 1
    assert rows[0]["type"] == "assignment.created"

    unread = api_client.get("/api/v1/notifications/", {"unread": "true"})
    assert len(unread.json()["results"]) == 1

    read = api_client.post(f"/api/v1/notifications/{rows[0]['uuid']}/read/", {}, format="json")
    assert read.status_code == 200
    assert read.json()["read_at"] is not None
    # Mark-read is idempotent.
    again = api_client.post(f"/api/v1/notifications/{rows[0]['uuid']}/read/", {}, format="json")
    assert again.status_code == 200
    assert api_client.get("/api/v1/notifications/", {"unread": "true"}).json()["results"] == []

    # Other users never see someone else's notification.
    api_client.force_authenticate(other)
    assert api_client.get("/api/v1/notifications/").json()["results"] == []
    not_found = api_client.post(f"/api/v1/notifications/{rows[0]['uuid']}/read/", {}, format="json")
    assert not_found.status_code == 404


def test_exception_report_notifies_managers(api_client, make_user, make_asset, workflow_reference):
    from apps.notifications.models import Notification

    operator = _operator(make_user, workflow_reference, "nt-operator-3")
    manager = make_user("nt-manager", "asset_manager")
    asset = make_asset("NT-003")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/report-exception/",
        {"report_type": "missing", "description": "Not at desk."},
        format="json",
    )
    assert Notification.objects.filter(recipient=manager, type="exception.reported").exists()


def test_due_reminders_dedupe(api_client, make_user, make_asset, workflow_reference):
    from apps.notifications.models import Notification
    from apps.notifications.services import generate_due_reminders

    make_user("nt-manager-2", "asset_manager")
    today = timezone.now().date()
    make_asset("NT-010", warranty_end=today + timedelta(days=10))
    make_asset("NT-011", next_maintenance_due=today - timedelta(days=1))

    first = generate_due_reminders(today=today)
    assert first["warranty.expiring"] == 1
    assert first["maintenance.due"] == 1
    # Second run the same day creates nothing new (dedupe key per asset per day).
    second = generate_due_reminders(today=today)
    assert second == {"warranty.expiring": 0, "maintenance.due": 0}
    assert Notification.objects.filter(type="warranty.expiring").count() == 1
    assert Notification.objects.filter(type="maintenance.due").count() == 1


def test_preferences_mute_optional_but_not_mandatory(
    api_client, make_user, make_asset, workflow_reference
):
    from apps.notifications.models import Notification

    operator = _operator(make_user, workflow_reference, "nt-operator-4")
    custodian = make_user("nt-custodian-4", "employee")

    api_client.force_authenticate(custodian)
    prefs = api_client.get("/api/v1/notifications/preferences/")
    assert prefs.status_code == 200
    assert "approval.decided" in prefs.json()["mandatory_types"]

    # Muting a mandatory compliance type is rejected.
    blocked = api_client.patch(
        "/api/v1/notifications/preferences/",
        {"muted_types": ["approval.decided"]},
        format="json",
    )
    assert blocked.status_code == 400

    # Muting an optional type works.
    muted = api_client.patch(
        "/api/v1/notifications/preferences/",
        {"muted_types": ["assignment.created"]},
        format="json",
    )
    assert muted.status_code == 200
    assert muted.json()["muted_types"] == ["assignment.created"]

    asset = make_asset("NT-020")
    api_client.force_authenticate(operator)
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/", {"custodian": str(custodian.uuid)}, format="json"
    )
    created = Notification.objects.filter(recipient=custodian, type="assignment.created")
    assert not created.exists()


def test_preferences_reject_unknown_types(api_client, make_user):
    user = make_user("nt-user", "employee")
    api_client.force_authenticate(user)
    response = api_client.patch(
        "/api/v1/notifications/preferences/", {"muted_types": ["bogus.type"]}, format="json"
    )
    assert response.status_code == 400
