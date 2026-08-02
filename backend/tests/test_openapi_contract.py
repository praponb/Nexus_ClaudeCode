"""OpenAPI contract tests: the published schema is the frontend contract
(design section 14.3). These fail the build when endpoints drift silently."""

import json
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")
pytest.importorskip("drf_spectacular")

pytestmark = pytest.mark.django_db

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"

EXPECTED_PATHS = {
    "/api/v1/auth/login/",
    "/api/v1/auth/logout/",
    "/api/v1/auth/me/",
    "/api/v1/auth/csrf/",
    "/api/v1/assets/",
    "/api/v1/assets/{uuid}/",
    "/api/v1/assets/{uuid}/history/",
    "/api/v1/assets/{uuid}/activity/",
    "/api/v1/assets/{uuid}/assign/",
    "/api/v1/assets/{uuid}/transfer/",
    "/api/v1/assets/{uuid}/return/",
    "/api/v1/assets/{uuid}/reserve/",
    "/api/v1/assets/{uuid}/checkout/",
    "/api/v1/assets/{uuid}/report-exception/",
    "/api/v1/assets/{uuid}/notes/",
    "/api/v1/assets/{uuid}/attachments/",
    "/api/v1/assets/{uuid}/label/",
    "/api/v1/assets/check-duplicates/",
    "/api/v1/assignments/",
    "/api/v1/maintenance/",
    "/api/v1/maintenance/{uuid}/complete/",
    "/api/v1/stocktakes/",
    "/api/v1/stocktakes/{uuid}/observations/",
    "/api/v1/stocktakes/{uuid}/start/",
    "/api/v1/stocktakes/{uuid}/reconcile/",
    "/api/v1/stocktakes/{uuid}/close/",
    "/api/v1/stocktakes/{uuid}/variance/",
    "/api/v1/imports/",
    "/api/v1/imports/template/",
    "/api/v1/imports/{uuid}/commit/",
    "/api/v1/imports/{uuid}/result/",
    "/api/v1/exports/",
    "/api/v1/exports/{uuid}/download/",
    "/api/v1/search/assets/",
    "/api/v1/dashboard/summary/",
    "/api/v1/data-quality/issues/",
    "/api/v1/saved-views/",
    "/api/v1/saved-views/{uuid}/",
    "/api/v1/reference-data/categories/",
    "/api/v1/reference-data/statuses/",
    "/api/v1/reference-data/conditions/",
    "/api/v1/reference-data/departments/",
    "/api/v1/reference-data/locations/",
    "/api/v1/reference-data/cost-centers/",
    "/api/v1/reference-data/suppliers/",
    "/api/v1/reference-data/maintenance-types/",
    "/api/v1/reference-data/transition-rules/",
    "/api/v1/health/live/",
    "/api/v1/health/ready/",
}


def _schema():
    from drf_spectacular.generators import SchemaGenerator

    return SchemaGenerator().get_schema(request=None, public=True)


def test_schema_contains_expected_paths():
    schema = _schema()
    missing = EXPECTED_PATHS - set(schema["paths"].keys())
    assert not missing, f"OpenAPI schema is missing expected paths: {sorted(missing)}"


def test_schema_is_valid_openapi3():
    schema = _schema()
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "Asset Inventory API"


def test_asset_endpoints_methods():
    schema = _schema()
    collection = schema["paths"]["/api/v1/assets/"]
    assert "get" in collection and "post" in collection
    detail = schema["paths"]["/api/v1/assets/{uuid}/"]
    assert "get" in detail and "patch" in detail


def test_asset_delete_is_rejected_with_envelope(api_client, authed, make_user, reference):
    """BR-003/FR-030: no destructive delete on business records."""
    admin = make_user("admin-del", "system_admin")
    client = authed(admin)
    response = client.post(
        "/api/v1/assets/",
        {
            "name": "Delete guard",
            "category": str(reference.category.uuid),
            "status": str(reference.draft.uuid),
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    asset_uuid = response.json()["asset"]["uuid"]
    response = client.delete(f"/api/v1/assets/{asset_uuid}/")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_schema_endpoint_served(api_client):
    response = api_client.get("/api/v1/schema/?format=json")
    assert response.status_code == 200


def test_committed_openapi_json_is_current():
    """backend/openapi.json is the frontend type-generation contract (design
    section 11.1). On drift this test regenerates the file and fails once, so
    the developer commits the updated artifact; the next run passes. The same
    regeneration is available via scripts/export-openapi.sh in compose.
    """
    rendered = json.dumps(_schema(), indent=2, sort_keys=True, default=str) + "\n"
    committed = OPENAPI_PATH.read_text() if OPENAPI_PATH.exists() else None
    if committed != rendered:
        OPENAPI_PATH.write_text(rendered)
        pytest.fail(
            "backend/openapi.json was stale (or missing) and has been regenerated. "
            "Review and commit the updated file, then re-run the tests."
        )
