"""CSV import/export (FR-018/FR-019): template, validate, policies,
formula-injection controls, field permissions, download authorization."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _upload(api_client, csv_text: str, policy: str = "skip", filename: str = "import.csv"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile(filename, csv_text.encode("utf-8"), content_type="text/csv")
    return api_client.post(
        "/api/v1/imports/", {"file": upload, "policy": policy}, format="multipart"
    )


def _commit(api_client, job_uuid: str):
    return api_client.post(f"/api/v1/imports/{job_uuid}/commit/", {}, format="json")


def _result_rows(api_client, job_uuid: str) -> list:
    response = api_client.get(f"/api/v1/imports/{job_uuid}/result/")
    assert response.status_code == 200
    return response.json()["rows"]


def _download_export(api_client, job_uuid: str) -> str:
    response = api_client.get(f"/api/v1/exports/{job_uuid}/download/")
    assert response.status_code == 200
    return b"".join(response.streaming_content).decode("utf-8-sig")


def test_template_download(api_client, make_user, reference):
    operator = make_user("bulk-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    response = api_client.get("/api/v1/imports/template/")
    assert response.status_code == 200
    assert "category_code" in response.json()["columns"]
    assert "tag" in response.json()["columns"]


def test_import_validate_and_commit_creates_assets(
    api_client, make_user, reference, settings, tmp_path
):
    from apps.assets.models import Asset

    settings.MEDIA_ROOT = str(tmp_path)
    operator = make_user("bulk-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    created = _upload(
        api_client, "tag,name,category_code,serial_number\nIMP-001,Widget,laptop,S-1\n"
    )
    assert created.status_code == 201, created.json()
    job = created.json()
    assert job["status"] == "validated"
    assert job["total_rows"] == 1

    committed = _commit(api_client, job["uuid"])
    assert committed.status_code == 200
    assert committed.json()["status"] == "completed"
    assert committed.json()["created_count"] == 1
    assert Asset.objects.filter(tag="IMP-001", name="Widget").exists()

    # Commit is safely repeatable (FR-018): no duplicate creation.
    again = _commit(api_client, job["uuid"])
    assert again.json()["created_count"] == 1
    assert Asset.objects.filter(tag="IMP-001").count() == 1

    assert _result_rows(api_client, job["uuid"])[0]["status"] == "created"


def test_import_duplicate_policies(api_client, make_user, reference, settings, tmp_path):
    from apps.assets.models import Asset

    settings.MEDIA_ROOT = str(tmp_path)
    operator = make_user("bulk-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    first = _upload(api_client, "tag,name,category_code\nIMP-100,Original,laptop\n")
    _commit(api_client, first.json()["uuid"])

    skipped = _upload(api_client, "tag,name,category_code\nIMP-100,Changed,laptop\n", policy="skip")
    skipped = _commit(api_client, skipped.json()["uuid"]).json()
    assert skipped["skipped_count"] == 1
    assert Asset.objects.get(tag="IMP-100").name == "Original"

    updated = _upload(
        api_client, "tag,name,category_code\nIMP-100,Changed,laptop\n", policy="update"
    )
    updated = _commit(api_client, updated.json()["uuid"]).json()
    assert updated["updated_count"] == 1
    assert Asset.objects.get(tag="IMP-100").name == "Changed"

    rejected = _upload(
        api_client, "tag,name,category_code\nIMP-100,Again,laptop\n", policy="reject"
    )
    rejected = _commit(api_client, rejected.json()["uuid"]).json()
    assert rejected["failed_count"] == 1
    assert Asset.objects.get(tag="IMP-100").name == "Changed"


def test_import_invalid_rows_reported(api_client, make_user, reference, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    operator = make_user("bulk-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    response = _upload(api_client, "name,category_code\nGhost,not-a-category\n,\n")
    assert response.status_code == 201
    job = response.json()
    assert job["failed_count"] == 2
    rows = _result_rows(api_client, job["uuid"])
    messages = [msg for row in rows for msg in row["messages"]]
    assert any("category_code" in message for message in messages)
    assert any("name is required" in message for message in messages)


def test_import_missing_required_columns_rejected(
    api_client, make_user, reference, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    operator = make_user("bulk-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    response = _upload(api_client, "foo,bar\n1,2\n")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMPORT_ROW_INVALID"


def test_import_formula_values_sanitized(api_client, make_user, reference, settings, tmp_path):
    from apps.assets.models import Asset

    settings.MEDIA_ROOT = str(tmp_path)
    operator = make_user("bulk-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    created = _upload(api_client, "name,category_code\n=HYPERLINK(1),laptop\n")
    assert created.status_code == 201
    row = _result_rows(api_client, created.json()["uuid"])[0]
    assert any("sanitized" in message for message in row["messages"])
    _commit(api_client, created.json()["uuid"])
    assert Asset.objects.filter(name="'=HYPERLINK(1)").exists()


def test_import_requires_edit_permission(api_client, make_user, reference, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    employee = make_user("bulk-emp", "employee")
    api_client.force_authenticate(employee)
    response = _upload(api_client, "name,category_code\nX,laptop\n")
    assert response.status_code == 403


def test_export_respects_finance_permission_and_sanitizes(
    api_client, make_user, make_asset, reference, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    make_asset("EXP-001", name="=EVIL()", purchase_price="100.00", purchase_currency="USD")
    manager = make_user("bulk-mgr", "asset_manager")
    api_client.force_authenticate(manager)
    created = api_client.post("/api/v1/exports/", {"filters": {}}, format="json")
    assert created.status_code == 201, created.json()
    job = created.json()
    assert job["status"] == "completed"
    assert job["row_count"] == 1

    content = _download_export(api_client, job["uuid"])
    header = content.splitlines()[0]
    assert "purchase_amount" in header
    # Formula-injection mitigation on export (FR-019).
    assert "'=EVIL()" in content

    # Operators do not receive finance columns.
    operator = make_user("bulk-op", "operator", scope_department=reference.department)
    api_client.force_authenticate(operator)
    op_created = api_client.post("/api/v1/exports/", {"filters": {}}, format="json")
    op_content = _download_export(api_client, op_created.json()["uuid"])
    assert "purchase_amount" not in op_content.splitlines()[0]


def test_export_download_hidden_from_other_users(
    api_client, make_user, make_asset, reference, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    make_asset("EXP-002")
    manager = make_user("bulk-mgr", "asset_manager")
    api_client.force_authenticate(manager)
    job = api_client.post("/api/v1/exports/", {"filters": {}}, format="json").json()
    other = make_user("bulk-other", "asset_manager")
    api_client.force_authenticate(other)
    # Another user's export job is not visible at all (existence not leaked).
    response = api_client.get(f"/api/v1/exports/{job['uuid']}/download/")
    assert response.status_code == 404
