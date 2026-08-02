import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _make_asset(reference, tag, name, status=None):
    from apps.assets.models import Asset

    return Asset.objects.create(
        tag=tag,
        name=name,
        category=reference.category,
        status=status or reference.in_stock,
        department=reference.department,
        location=reference.location,
    )


def test_search_exact_tag_first(api_client, authed, make_user, reference):
    _make_asset(reference, "AST-111111", "Alpha laptop")
    _make_asset(reference, "AST-222222", "Spare AST-111111 cable")
    manager = make_user("mgr-search", "asset_manager")
    response = authed(manager).get("/api/v1/search/assets/?q=AST-111111")
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["tag"] == "AST-111111"
    assert results[0]["match"] == "exact"


def test_search_requires_query(api_client, authed, make_user, reference):
    manager = make_user("mgr-search2", "asset_manager")
    response = authed(manager).get("/api/v1/search/assets/")
    assert response.status_code == 400
    assert "q" in response.json()["error"]["field_errors"]


def test_dashboard_summary_counts(api_client, authed, make_user, reference):
    _make_asset(reference, "AST-333333", "One")
    _make_asset(reference, "AST-444444", "Two")
    manager = make_user("mgr-dash", "asset_manager")
    response = authed(manager).get("/api/v1/dashboard/summary/")
    assert response.status_code == 200
    body = response.json()
    assert body["total_assets"] == 2
    assert body["scope"] == "global"
    assert body["unassigned"] == 2
    assert any(row["code"] == "in_stock" for row in body["by_status"])
    assert "generated_at" in body


def test_saved_views_crud_and_sharing(api_client, authed, make_user, reference):
    owner = make_user("owner-sv", "operator")
    other = make_user("other-sv", "operator")

    client = authed(owner)
    response = client.post(
        "/api/v1/saved-views/",
        {"name": "My view", "config": {"filters": {"status_code": "in_stock"}}},
        format="json",
    )
    assert response.status_code == 201, response.json()
    view_uuid = response.json()["uuid"]

    # Private view is invisible (404) to other users.
    assert authed(other).get(f"/api/v1/saved-views/{view_uuid}/").status_code == 404

    # Share it; now readable by others but not modifiable.
    response = authed(owner).patch(
        f"/api/v1/saved-views/{view_uuid}/", {"shared": True}, format="json"
    )
    assert response.status_code == 200
    assert authed(other).get(f"/api/v1/saved-views/{view_uuid}/").status_code == 200
    assert (
        authed(other)
        .patch(f"/api/v1/saved-views/{view_uuid}/", {"name": "Hijack"}, format="json")
        .status_code
        == 403
    )

    # Owner can delete.
    assert authed(owner).delete(f"/api/v1/saved-views/{view_uuid}/").status_code == 204
