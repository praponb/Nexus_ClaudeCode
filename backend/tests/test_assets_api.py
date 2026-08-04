import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _payload(reference, **overrides):
    payload = {
        "name": "Developer laptop",
        "category": str(reference.category.uuid),
        "status": str(reference.in_stock.uuid),
        "condition": str(reference.condition.uuid),
        "department": str(reference.department.uuid),
        "location": str(reference.location.uuid),
        "acquisition_type": "purchased",
    }
    payload.update(overrides)
    return payload


def _create(client, reference, **overrides):
    response = client.post("/api/v1/assets/", _payload(reference, **overrides), format="json")
    assert response.status_code == 201, response.json()
    return response.json()["asset"]


def _scoped_operator(make_user, username, reference):
    """Operators work within an organizational scope (design section 9.3)."""
    return make_user(username, "operator", scope_department=reference.department)


def test_create_asset_success_with_audit_and_lifecycle(api_client, authed, make_user, reference):
    from apps.assets.models import Asset, LifecycleEvent
    from apps.audit.models import AuditEvent

    operator = _scoped_operator(make_user, "op-create", reference)
    client = authed(operator)
    response = client.post("/api/v1/assets/", _payload(reference), format="json")
    assert response.status_code == 201
    body = response.json()
    asset = body["asset"]
    assert asset["tag"].startswith("AST-")
    assert asset["version"] == 1
    assert body["warnings"] == []
    stored = Asset.objects.get(uuid=asset["uuid"])
    assert LifecycleEvent.objects.filter(asset=stored, event_type="registered").exists()
    assert AuditEvent.objects.filter(
        action="asset.create", target_uuid=stored.uuid, outcome="success"
    ).exists()


def test_create_asset_validation_error_envelope(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-val", reference)
    client = authed(operator)
    payload = _payload(reference)
    del payload["name"]
    response = client.post("/api/v1/assets/", payload, format="json")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_FAILED"
    assert "name" in error["field_errors"]


def test_operational_fields_required_unless_draft(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-req", reference)
    client = authed(operator)
    payload = {
        "name": "No condition",
        "category": str(reference.category.uuid),
        "status": str(reference.in_stock.uuid),
        "department": str(reference.department.uuid),
        "location": str(reference.location.uuid),
        "acquisition_type": "purchased",
    }
    response = client.post("/api/v1/assets/", payload, format="json")
    assert response.status_code == 400
    assert "condition" in response.json()["error"]["field_errors"]

    draft_payload = {
        "name": "Draft asset",
        "category": str(reference.category.uuid),
        "status": str(reference.draft.uuid),
    }
    response = client.post("/api/v1/assets/", draft_payload, format="json")
    assert response.status_code == 201, response.json()


def test_duplicate_tag_conflict(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-dup", reference)
    client = authed(operator)
    _create(client, reference, tag="AST-900001")
    response = client.post("/api/v1/assets/", _payload(reference, tag="AST-900001"), format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_TAG"


def test_employee_cannot_create(api_client, authed, make_user, reference):
    employee = make_user("emp-create", "employee")
    client = authed(employee)
    response = client.post("/api/v1/assets/", _payload(reference), format="json")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_list_pagination_envelope_and_page_size_cap(api_client, authed, make_user, reference):
    from apps.assets.models import Asset

    manager = make_user("mgr-list", "asset_manager")
    for index in range(30):
        Asset.objects.create(
            tag=f"AST-7{index:05d}",
            name=f"Asset {index}",
            category=reference.category,
            status=reference.in_stock,
        )
    client = authed(manager)
    response = client.get("/api/v1/assets/")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"count", "next", "previous", "results"}
    assert body["count"] == 30
    assert len(body["results"]) == 25
    response = client.get("/api/v1/assets/?page_size=500")
    assert len(response.json()["results"]) == 30  # capped at max_page_size=100


def test_out_of_scope_asset_returns_404(api_client, authed, make_user, reference):
    from apps.assets.models import Asset

    admin = make_user("admin-scope", "system_admin")
    asset = _create(authed(admin), reference, department=str(reference.other_department.uuid))
    assert Asset.objects.filter(uuid=asset["uuid"]).exists()

    operator = _scoped_operator(make_user, "op-scope", reference)
    response = authed(operator).get(f"/api/v1/assets/{asset['uuid']}/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_update_requires_version(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-nov", reference)
    client = authed(operator)
    asset = _create(client, reference)
    response = client.patch(f"/api/v1/assets/{asset['uuid']}/", {"name": "Renamed"}, format="json")
    assert response.status_code == 400
    assert "version" in response.json()["error"]["field_errors"]


def test_update_stale_version_conflict(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-stale", reference)
    client = authed(operator)
    asset = _create(client, reference)
    response = client.patch(
        f"/api/v1/assets/{asset['uuid']}/",
        {"name": "Renamed", "version": asset["version"] + 5},
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"


def test_update_success_bumps_version_and_audits(api_client, authed, make_user, reference):
    from apps.assets.models import LifecycleEvent
    from apps.audit.models import AuditEvent

    operator = _scoped_operator(make_user, "op-ok", reference)
    client = authed(operator)
    asset = _create(client, reference)
    response = client.patch(
        f"/api/v1/assets/{asset['uuid']}/",
        {
            "name": "Renamed laptop",
            "status": str(reference.assigned.uuid),
            "version": asset["version"],
        },
        format="json",
    )
    assert response.status_code == 200, response.json()
    updated = response.json()
    assert updated["version"] == asset["version"] + 1
    assert updated["name"] == "Renamed laptop"
    assert updated["status"]["code"] == "assigned"
    assert LifecycleEvent.objects.filter(
        asset__uuid=asset["uuid"], event_type="status_changed"
    ).exists()
    assert AuditEvent.objects.filter(action="asset.update", target_uuid=asset["uuid"]).exists()


def test_invalid_status_transition_rejected(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-trans", reference)
    client = authed(operator)
    asset = _create(client, reference)
    response = client.patch(
        f"/api/v1/assets/{asset['uuid']}/",
        {"status": str(reference.disposed.uuid), "version": asset["version"]},
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATUS_TRANSITION_INVALID"


def test_tag_is_immutable(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-tag", reference)
    client = authed(operator)
    asset = _create(client, reference)
    response = client.patch(
        f"/api/v1/assets/{asset['uuid']}/",
        {"tag": "AST-000999", "version": asset["version"]},
        format="json",
    )
    assert response.status_code == 400
    assert "tag" in response.json()["error"]["field_errors"]


def test_finance_fields_hidden_from_operator(api_client, authed, make_user, reference):
    admin = make_user("admin-fin", "system_admin")
    asset = _create(authed(admin), reference, purchase={"amount": "1200.00", "currency": "USD"})
    operator = _scoped_operator(make_user, "op-fin", reference)
    response = authed(operator).get(f"/api/v1/assets/{asset['uuid']}/")
    assert response.status_code == 200
    assert "purchase" not in response.json()
    assert "po_reference" not in response.json()


def test_finance_fields_visible_to_auditor(api_client, authed, make_user, reference):
    admin = make_user("admin-fin2", "system_admin")
    asset = _create(authed(admin), reference, purchase={"amount": "1200.00", "currency": "USD"})
    auditor = make_user("aud-fin", "auditor")
    response = authed(auditor).get(f"/api/v1/assets/{asset['uuid']}/")
    assert response.status_code == 200
    assert response.json()["purchase"] == {"amount": "1200.00", "currency": "USD"}


def test_check_duplicates_endpoint_warns(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-dupwarn", reference)
    client = authed(operator)
    _create(client, reference, serial_number="SN-DUP-1")
    response = client.post(
        "/api/v1/assets/check-duplicates/", {"serial_number": "SN-DUP-1"}, format="json"
    )
    assert response.status_code == 200
    warnings = response.json()["warnings"]
    assert warnings[0]["code"] == "POSSIBLE_DUPLICATE_SERIAL"


def test_history_endpoint_returns_lifecycle_and_audit(api_client, authed, make_user, reference):
    operator = _scoped_operator(make_user, "op-hist", reference)
    client = authed(operator)
    asset = _create(client, reference)
    response = client.get(f"/api/v1/assets/{asset['uuid']}/history/")
    assert response.status_code == 200
    types = {event["type"] for event in response.json()["results"]}
    assert {"lifecycle", "audit"} <= types


def test_list_free_text_search_filters_on_q(api_client, authed, make_user, reference):
    """The register's free-text box sends `?q=` (FR-005). It must actually
    narrow the list -- returning every asset unfiltered silently defeats the
    filter and misleads the user, since the UI still shows a "Search:" chip.
    """
    operator = _scoped_operator(make_user, "op-searchq", reference)
    client = authed(operator)
    _create(client, reference, name="Developer laptop", serial_number="SN-Q-1")
    _create(client, reference, name="Warehouse forklift", serial_number="SN-Q-2")

    response = client.get("/api/v1/assets/?q=forklift")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1, "q must narrow the result set, not be ignored"
    assert body["results"][0]["name"] == "Warehouse forklift"


def test_list_free_text_search_covers_every_advertised_field(
    api_client, authed, make_user, reference
):
    """The filter input is labelled "tag, serial, name, model, custodian, or
    location" and the Help page repeats that promise, so each of those fields
    must be searchable from the list endpoint.
    """
    from apps.assets.models import Asset

    operator = _scoped_operator(make_user, "op-searchfields", reference)
    client = authed(operator)
    custodian = make_user("keeper-jane", "employee", department=reference.department)
    asset = _create(
        client,
        reference,
        name="Developer laptop",
        serial_number="SN-FIELDS-9",
        manufacturer="Dell",
        model="Latitude-5540",
    )
    Asset.objects.filter(uuid=asset["uuid"]).update(custodian=custodian)
    _create(client, reference, name="Unrelated monitor", serial_number="SN-OTHER-9")

    for term in [
        asset["tag"],
        "SN-FIELDS-9",
        "Developer",
        "Latitude-5540",
        "keeper-jane",
        reference.location.name,
    ]:
        response = client.get("/api/v1/assets/", {"q": term})
        assert response.status_code == 200, term
        tags = {row["tag"] for row in response.json()["results"]}
        assert asset["tag"] in tags, f"q={term!r} did not match on an advertised field"


def test_list_free_text_search_respects_scope(api_client, authed, make_user, reference):
    """Search must not become a way around organizational scope (FR-002)."""
    from apps.assets.models import Asset

    owner = _scoped_operator(make_user, "op-scope-owner", reference)
    asset = _create(authed(owner), reference, name="Secret prototype")
    Asset.objects.filter(uuid=asset["uuid"]).update(department=reference.other_department)

    outsider = _scoped_operator(make_user, "op-scope-outsider", reference)
    response = authed(outsider).get("/api/v1/assets/?q=Secret")
    assert response.status_code == 200
    assert response.json()["count"] == 0
