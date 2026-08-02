import io

import pytest

pytest.importorskip("django")


@pytest.mark.django_db
def test_no_pending_model_changes():
    """Mirrors `manage.py makemigrations --check --dry-run` (CI quality gate).

    Fails if any model change lacks a committed migration file.
    """
    from django.core.management import call_command

    out = io.StringIO()
    try:
        call_command("makemigrations", check=True, dry_run=True, verbosity=3, stdout=out)
    except SystemExit as exc:
        raise AssertionError(f"Unmigrated model changes detected:\n{out.getvalue()}") from exc


@pytest.mark.django_db(transaction=True)
def test_seed_dev_is_idempotent_and_complete():
    """Seed data (design 10.4) must be safely re-runnable (stack section 13)."""
    from django.core.management import call_command

    from apps.accounts.models import User
    from apps.assets.models import Asset
    from apps.reference_data.models import AssetCondition, AssetStatus, Department, Location

    call_command("seed_dev", verbosity=0)
    counts = (
        AssetStatus.objects.count(),
        AssetCondition.objects.count(),
        Department.objects.count(),
        Location.objects.count(),
        User.objects.count(),
        Asset.objects.count(),
    )
    assert counts[0] == 13  # default statuses per spec section 8.1
    assert counts[1] == 6  # default conditions per spec section 8.2
    assert counts[2] >= 8
    assert counts[3] >= 12
    assert counts[4] >= 6  # one demo user per role
    assert counts[5] == 200

    # Second run must not duplicate anything.
    call_command("seed_dev", verbosity=0)
    assert AssetStatus.objects.count() == counts[0]
    assert Asset.objects.count() == counts[5]
    assert User.objects.count() == counts[4]
