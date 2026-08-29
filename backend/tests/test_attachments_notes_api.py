"""Attachments (FR-015, D-04), notes (FR-016), activity feed (FR-029),
QR label (FR-017, D-14)."""

import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")

pytestmark = pytest.mark.django_db


def _operator(make_user, reference, username="att-operator"):
    return make_user(username, "operator", scope_department=reference.department)


def _upload(api_client, asset_uuid, name="hello.txt", content=b"hello world"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile(name, content, content_type="text/plain")
    return api_client.post(
        f"/api/v1/assets/{asset_uuid}/attachments/", {"file": upload}, format="multipart"
    )


def test_attachment_upload_download_delete_cycle(
    api_client, make_user, make_asset, reference, settings, tmp_path
):
    from apps.audit.models import AuditEvent

    settings.MEDIA_ROOT = str(tmp_path)
    operator = _operator(make_user, reference)
    asset = make_asset("ATT-001")
    api_client.force_authenticate(operator)

    uploaded = _upload(api_client, asset.uuid)
    assert uploaded.status_code == 201, uploaded.json()
    attachment = uploaded.json()
    assert attachment["filename"] == "hello.txt"
    assert attachment["size"] == len(b"hello world")

    listed = api_client.get(f"/api/v1/assets/{asset.uuid}/attachments/")
    assert [row["uuid"] for row in listed.json()["results"]] == [attachment["uuid"]]

    downloaded = api_client.get(
        f"/api/v1/assets/{asset.uuid}/attachments/{attachment['uuid']}/download/"
    )
    assert downloaded.status_code == 200
    assert b"".join(downloaded.streaming_content) == b"hello world"

    deleted = api_client.delete(f"/api/v1/assets/{asset.uuid}/attachments/{attachment['uuid']}/")
    assert deleted.status_code == 204
    assert api_client.get(f"/api/v1/assets/{asset.uuid}/attachments/").json()["results"] == []

    actions = set(
        AuditEvent.objects.filter(target_uuid=asset.uuid).values_list("action", flat=True)
    )
    assert {"attachment.upload", "attachment.download", "attachment.remove"} <= actions


def test_attachment_validation_rejects_bad_files(
    api_client, make_user, make_asset, reference, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    operator = _operator(make_user, reference)
    asset = make_asset("ATT-002")
    api_client.force_authenticate(operator)

    bad_extension = _upload(api_client, asset.uuid, name="evil.exe", content=b"MZ")
    assert bad_extension.status_code == 415

    bad_signature = _upload(api_client, asset.uuid, name="fake.png", content=b"not-a-png")
    assert bad_signature.status_code == 415

    empty = _upload(api_client, asset.uuid, content=b"")
    assert empty.status_code == 400


def test_attachment_requires_edit_permission(
    api_client, make_user, make_asset, reference, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    employee = make_user("att-employee", "employee")
    asset = make_asset("ATT-003", custodian=employee)
    api_client.force_authenticate(employee)
    response = _upload(api_client, asset.uuid)
    assert response.status_code == 403


def test_attachment_download_hidden_across_scopes(
    api_client, make_user, make_asset, reference, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    operator = _operator(make_user, reference)
    outsider = make_user("att-outsider", "operator", scope_department=reference.other_department)
    asset = make_asset("ATT-004")
    api_client.force_authenticate(operator)
    attachment = _upload(api_client, asset.uuid).json()

    api_client.force_authenticate(outsider)
    response = api_client.get(
        f"/api/v1/assets/{asset.uuid}/attachments/{attachment['uuid']}/download/"
    )
    assert response.status_code == 404


def test_notes_create_list_and_validation(api_client, make_user, make_asset, reference):
    operator = _operator(make_user, reference)
    asset = make_asset("ATT-005")
    api_client.force_authenticate(operator)

    empty = api_client.post(f"/api/v1/assets/{asset.uuid}/notes/", {"body": " "}, format="json")
    assert empty.status_code == 400
    assert "body" in empty.json()["error"]["field_errors"]

    created = api_client.post(
        f"/api/v1/assets/{asset.uuid}/notes/", {"body": "Inspected on site."}, format="json"
    )
    assert created.status_code == 201
    assert created.json()["author"] is not None

    listed = api_client.get(f"/api/v1/assets/{asset.uuid}/notes/")
    bodies = [row["body"] for row in listed.json()["results"]]
    assert bodies == ["Inspected on site."]


def test_activity_feed_combines_event_types(api_client, make_user, make_asset, reference):
    operator = _operator(make_user, reference)
    asset = make_asset("ATT-006")
    api_client.force_authenticate(operator)
    api_client.post(f"/api/v1/assets/{asset.uuid}/notes/", {"body": "Feed note."}, format="json")
    api_client.post(
        f"/api/v1/assets/{asset.uuid}/assign/",
        {"department": str(reference.department.uuid)},
        format="json",
    )
    response = api_client.get(f"/api/v1/assets/{asset.uuid}/activity/")
    assert response.status_code == 200
    types = {item["type"] for item in response.json()["results"]}
    assert {"note", "lifecycle", "audit"} <= types
    summaries = [item["summary"] for item in response.json()["results"]]
    assert "Feed note." in summaries


def test_label_returns_qr_svg_and_deep_link(api_client, make_user, make_asset, reference):
    pytest.importorskip("qrcode")
    operator = _operator(make_user, reference)
    asset = make_asset("ATT-007")
    api_client.force_authenticate(operator)
    response = api_client.get(f"/api/v1/assets/{asset.uuid}/label/")
    assert response.status_code == 200
    body = response.json()
    assert body["tag"] == "ATT-007"
    assert body["url"].endswith("/scan?tag=ATT-007")
    assert "svg" in body["svg"].lower()
    assert body["label"] == {"width_mm": 50, "height_mm": 25}


def test_dockerfile_creates_media_dir_owned_by_appuser():
    """The upload tests above run against a tmp_path MEDIA_ROOT, which is exactly
    why they never caught the real defect: in the built image /app/media did not
    exist, so Docker created the volume mount point as root and every upload
    failed with PermissionError. This guard is image-level because the bug was.
    """
    from pathlib import Path

    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
    lines = dockerfile.read_text().splitlines()

    setup = [i for i, line in enumerate(lines) if "mkdir -p /app/media" in line]
    assert setup, "Dockerfile must create /app/media in the image, not rely on the volume mount"
    assert "chown -R appuser:appuser /app" in lines[setup[0]], (
        "/app/media must be chowned in the same layer that creates it"
    )

    switches = [i for i, line in enumerate(lines) if line.strip() == "USER appuser"]
    assert switches, "Dockerfile must drop privileges to appuser"
    assert setup[0] < switches[0], "the chown must run before the image drops to appuser"
