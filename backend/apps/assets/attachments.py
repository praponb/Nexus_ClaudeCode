"""Attachment validation + storage helpers (FR-015, D-04).

Validation layers: extension allowlist, size limit, content signature (magic
bytes) for binary formats, filename sanitization, random storage keys.
Downloads are only ever served through the authorized endpoint.
"""

import contextlib
import os
import re
import uuid as uuid_module
from pathlib import Path

from django.conf import settings

from apps.core.exceptions import ApiException

SIGNATURES: dict[str, bytes] = {
    "png": b"\x89PNG\r\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "gif": b"GIF8",
    "webp": b"RIFF",
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",
    "xlsx": b"PK\x03\x04",
}
# Text formats carry no reliable binary signature.
TEXT_EXTENSIONS = {"txt", "csv"}

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(raw_name: str) -> str:
    basename = os.path.basename(raw_name or "")
    sanitized = SAFE_FILENAME_RE.sub("_", basename).strip("._")
    return sanitized[:120] or "attachment"


def validate_upload(*, filename: str, content: bytes) -> tuple[str, str]:
    """Returns (sanitized_filename, extension). Raises ApiException on failure."""
    if not content:
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "The uploaded file is empty.",
            field_errors={"file": ["Provide a non-empty file."]},
        )
    if len(content) > settings.ATTACHMENT_MAX_BYTES:
        raise ApiException(
            413,
            "UPLOAD_TOO_LARGE",
            "The uploaded file exceeds the maximum allowed size.",
        )
    sanitized = sanitize_filename(filename)
    extension = sanitized.rsplit(".", 1)[-1].lower() if "." in sanitized else ""
    if extension not in settings.ATTACHMENT_ALLOWED_EXTENSIONS:
        raise ApiException(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "This file type is not allowed.",
            field_errors={
                "file": ["Allowed types: " + ", ".join(settings.ATTACHMENT_ALLOWED_EXTENSIONS)]
            },
        )
    signature = SIGNATURES.get(extension)
    if signature is not None and not content.startswith(signature):
        raise ApiException(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "The file content does not match its extension.",
            field_errors={"file": ["File signature validation failed."]},
        )
    return sanitized, extension


def store_upload(asset_uuid, content: bytes, extension: str) -> str:
    """Write to a random storage key under MEDIA_ROOT; return the key."""
    storage_key = f"attachments/{asset_uuid}/{uuid_module.uuid4().hex}.{extension}"
    target = Path(settings.MEDIA_ROOT) / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return storage_key


def remove_stored(storage_key: str) -> None:
    target = Path(settings.MEDIA_ROOT) / storage_key
    with contextlib.suppress(FileNotFoundError):
        target.unlink()
