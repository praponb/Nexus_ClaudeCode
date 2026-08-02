import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

from datetime import date  # noqa: E402

pytestmark = pytest.mark.django_db(transaction=True)


def _asset(reference, tag):
    from apps.assets.models import Asset

    return Asset(
        tag=tag,
        name=f"Asset {tag}",
        category=reference.category,
        status=reference.in_stock,
    )


def test_asset_tag_unique_constraint(reference):
    from django.db import IntegrityError, transaction

    _asset(reference, "AST-777777").save()
    with pytest.raises(IntegrityError), transaction.atomic():
        _asset(reference, "AST-777777").save()


def test_one_active_assignment_per_asset(reference, make_user):
    from django.db import IntegrityError, transaction

    from apps.assignments.models import Assignment

    asset = _asset(reference, "AST-888888")
    asset.save()
    user = make_user("assign-user", "employee")
    Assignment.objects.create(asset=asset, custodian=user)
    with pytest.raises(IntegrityError), transaction.atomic():
        Assignment.objects.create(asset=asset, custodian=user)


def test_warranty_date_check_constraint(reference):
    from django.db import IntegrityError, transaction

    asset = _asset(reference, "AST-999999")
    asset.warranty_start = date(2024, 6, 1)
    asset.warranty_end = date(2024, 1, 1)
    with pytest.raises(IntegrityError), transaction.atomic():
        asset.save()
