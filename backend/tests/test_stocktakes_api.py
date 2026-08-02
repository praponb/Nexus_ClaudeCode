"""Stocktake sessions, observations, reconciliation, variance (FR-022)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _create_session(api_client, name="Q3 count", locations=None):
    payload = {"name": name}
    if locations is not None:
        payload["locations"] = [str(location.uuid) for location in locations]
    response = api_client.post("/api/v1/stocktakes/", payload, format="json")
    assert response.status_code == 201, response.json()
    return response.json()


def _observe(api_client, session_uuid, idempotency_key=None, **payload):
    extra = {"HTTP_IDEMPOTENCY_KEY": idempotency_key} if idempotency_key else {}
    return api_client.post(
        f"/api/v1/stocktakes/{session_uuid}/observations/", payload, format="json", **extra
    )


def test_session_lifecycle_and_outcomes(api_client, make_user, make_asset, workflow_reference):
    from apps.reference_data.models import Location

    manager = make_user("st-manager", "asset_manager")
    operator = make_user("st-operator", "operator")
    ref = workflow_reference
    other_location = Location.objects.create(code="wh", name="Warehouse")
    asset_found = make_asset("ST-001")
    asset_moved = make_asset("ST-002")
    asset_mismatch = make_asset("ST-003")
    asset_absent = make_asset("ST-004")

    api_client.force_authenticate(manager)
    session = _create_session(api_client, locations=[ref.location])
    session_uuid = session["uuid"]
    assert session["status"] == "draft"

    started = api_client.post(f"/api/v1/stocktakes/{session_uuid}/start/", {}, format="json")
    assert started.status_code == 200
    assert started.json()["status"] == "open"
    assert started.json()["snapshot_at"] is not None
    restart = api_client.post(f"/api/v1/stocktakes/{session_uuid}/start/", {}, format="json")
    assert restart.status_code == 409
    assert restart.json()["error"]["code"] == "STOCKTAKE_STATE_INVALID"

    # Closing before reconciliation is rejected.
    early_close = api_client.post(f"/api/v1/stocktakes/{session_uuid}/close/", {}, format="json")
    assert early_close.status_code == 409

    api_client.force_authenticate(operator)
    found = _observe(
        api_client,
        session_uuid,
        tag_scanned=asset_found.tag,
        location=str(ref.location.uuid),
        condition=str(ref.condition.uuid),
    )
    assert found.status_code == 201, found.json()
    assert found.json()["outcome"] == "found"

    duplicate = _observe(api_client, session_uuid, tag_scanned=asset_found.tag)
    assert duplicate.json()["outcome"] == "duplicate"

    unexpected = _observe(api_client, session_uuid, tag_scanned="NO-SUCH-TAG")
    assert unexpected.json()["outcome"] == "unexpected"

    moved = _observe(
        api_client, session_uuid, tag_scanned=asset_moved.tag, location=str(other_location.uuid)
    )
    assert moved.json()["outcome"] == "moved"

    mismatch = _observe(
        api_client, session_uuid, tag_scanned=asset_mismatch.tag, condition=str(ref.damaged.uuid)
    )
    assert mismatch.json()["outcome"] == "condition_mismatch"

    variance = api_client.get(f"/api/v1/stocktakes/{session_uuid}/variance/")
    assert variance.status_code == 200
    body = variance.json()
    assert body["expected_count"] == 4
    assert body["found_count"] == 3
    assert [row["tag"] for row in body["not_found"]] == [asset_absent.tag]
    assert len(body["unexpected"]) == 1
    assert len(body["duplicates"]) == 1

    # Reconciliation applies reviewed master-data updates.
    api_client.force_authenticate(manager)
    reconciled = api_client.post(f"/api/v1/stocktakes/{session_uuid}/reconcile/", {}, format="json")
    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "reconciling"
    asset_moved.refresh_from_db()
    assert asset_moved.location == other_location
    asset_mismatch.refresh_from_db()
    assert asset_mismatch.condition.code == "damaged"

    closed = api_client.post(f"/api/v1/stocktakes/{session_uuid}/close/", {}, format="json")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    # Observations are rejected once the session is no longer open.
    api_client.force_authenticate(operator)
    late = _observe(api_client, session_uuid, tag_scanned=asset_absent.tag)
    assert late.status_code == 409


def test_session_create_requires_manager(api_client, make_user, workflow_reference):
    operator = make_user("st-op-only", "operator")
    api_client.force_authenticate(operator)
    response = api_client.post("/api/v1/stocktakes/", {"name": "Nope"}, format="json")
    assert response.status_code == 403


def test_observation_requires_operator_role(api_client, make_user, workflow_reference):
    manager = make_user("st-mgr-2", "asset_manager")
    employee = make_user("st-employee", "employee")
    api_client.force_authenticate(manager)
    session = _create_session(api_client, name="Employee check")
    api_client.post(f"/api/v1/stocktakes/{session['uuid']}/start/", {}, format="json")
    api_client.force_authenticate(employee)
    response = _observe(api_client, session["uuid"], tag_scanned="ANY")
    assert response.status_code == 403


def test_observation_requires_tag(api_client, make_user, workflow_reference):
    manager = make_user("st-mgr-3", "asset_manager")
    api_client.force_authenticate(manager)
    session = _create_session(api_client, name="Tag check")
    api_client.post(f"/api/v1/stocktakes/{session['uuid']}/start/", {}, format="json")
    response = _observe(api_client, session["uuid"], tag_scanned="")
    assert response.status_code == 400
    assert "tag_scanned" in response.json()["error"]["field_errors"]


def test_observation_recording_is_idempotent(api_client, make_user, make_asset, workflow_reference):
    from apps.stocktakes.models import StocktakeObservation

    manager = make_user("st-mgr-4", "asset_manager")
    operator = make_user("st-op-4", "operator")
    asset = make_asset("ST-100")
    api_client.force_authenticate(manager)
    session = _create_session(api_client, name="Idempotent scan")
    session_uuid = session["uuid"]
    api_client.post(f"/api/v1/stocktakes/{session_uuid}/start/", {}, format="json")
    api_client.force_authenticate(operator)
    first = _observe(api_client, session_uuid, idempotency_key="scan-key-1", tag_scanned=asset.tag)
    assert first.status_code == 201
    replay = _observe(api_client, session_uuid, idempotency_key="scan-key-1", tag_scanned=asset.tag)
    assert replay.status_code == 201
    assert replay.json()["uuid"] == first.json()["uuid"]
    # The replayed scan did not create a duplicate observation.
    assert StocktakeObservation.objects.filter(session__uuid=session_uuid).count() == 1
