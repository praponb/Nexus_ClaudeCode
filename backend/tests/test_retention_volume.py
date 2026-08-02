"""FR-030 legal hold + NFR-004/006 volume generation and query discipline."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _create_asset(client, reference):
    response = client.post(
        "/api/v1/assets/",
        {
            "name": "Hold target",
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
    return response.json()["asset"]


def test_legal_hold_admin_only(api_client, make_user, reference):
    admin = make_user("hold-admin", "system_admin")
    operator = make_user("hold-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(admin)
    asset = _create_asset(api_client, reference)

    # Operators may not set the legal hold.
    api_client.force_authenticate(operator)
    denied = api_client.patch(
        f"/api/v1/assets/{asset['uuid']}/",
        {"legal_hold": True, "version": asset["version"]},
        format="json",
    )
    assert denied.status_code == 403

    # System administrators may; the change is audited and visible.
    api_client.force_authenticate(admin)
    allowed = api_client.patch(
        f"/api/v1/assets/{asset['uuid']}/",
        {"legal_hold": True, "version": asset["version"]},
        format="json",
    )
    assert allowed.status_code == 200, allowed.json()
    assert allowed.json()["legal_hold"] is True


def test_generate_volume_command_and_query_discipline(
    api_client, make_user, reference, django_assert_num_queries
):
    from django.core.management import call_command

    from apps.assets.models import Asset

    call_command("generate_volume", assets=120, batch=60, verbosity=0)
    assert Asset.objects.filter(tag__startswith="VOL-").count() == 120
    # Repeat runs stay unique (prefix counter continues).
    call_command("generate_volume", assets=10, verbosity=0)
    assert Asset.objects.filter(tag__startswith="VOL-").count() == 130

    admin = make_user("vol-admin", "system_admin")
    api_client.force_authenticate(admin)
    # Hot endpoint stays N+1-free with volume data present (NFR-004): a small,
    # constant query count regardless of row count (count + page queries).
    with django_assert_num_queries(5, exact=False):
        response = api_client.get("/api/v1/assets/")
    assert response.status_code == 200
    assert response.json()["count"] == 130
