"""CSV import/export services (FR-018/FR-019).

Import: template -> upload/validate (preview) -> commit (idempotent,
safely repeatable) -> per-row result report. Cells are treated as text;
formula-like leading characters are sanitized and flagged (never executed).
Export: permission-scoped queryset, finance columns only with finance.view,
UTF-8 with BOM, formula-injection mitigation.
"""

import csv
import io
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import transaction

from apps.assets.models import Asset
from apps.assets.services import create_asset, update_asset
from apps.audit.services import record_audit
from apps.bulk.models import ExportJob, ImportJob
from apps.core.csv_utils import DANGEROUS_PREFIXES, sanitize_csv_value
from apps.core.exceptions import ApiException
from apps.core.permissions import scope_assets
from apps.reference_data.models import (
    AssetCondition,
    AssetStatus,
    Category,
    Department,
    Location,
)

TEMPLATE_COLUMNS = [
    "tag",
    "name",
    "category_code",
    "status_code",
    "condition_code",
    "department_code",
    "location_code",
    "serial_number",
    "manufacturer",
    "model",
    "acquisition_type",
    "purchase_date",
    "purchase_amount",
    "purchase_currency",
    "warranty_start",
    "warranty_end",
]

EXPORT_BASE_COLUMNS = [
    "tag",
    "name",
    "status",
    "condition",
    "category",
    "department",
    "location",
    "custodian",
    "serial_number",
    "manufacturer",
    "model",
    "acquisition_type",
    "purchase_date",
    "warranty_start",
    "warranty_end",
    "next_maintenance_due",
    "created_at",
]

EXPORT_FINANCE_COLUMNS = ["purchase_amount", "purchase_currency"]

MAX_IMPORT_ROWS = 25_000


def template_csv() -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(TEMPLATE_COLUMNS)
    return buffer.getvalue()


def _sanitize_cell(value: str) -> tuple[str, bool]:
    """Cells are text; formula-like values are prefixed (never executed)."""
    if value.startswith(DANGEROUS_PREFIXES):
        return sanitize_csv_value(value), True
    return value, False


def _parse_date(raw: str):
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _require(condition: bool, message: str, messages: list[str]) -> None:
    """Collect a row-validation message when ``condition`` is false."""
    if not condition:
        messages.append(message)


def validate_import_csv(file_bytes: bytes) -> tuple[list[dict], list[dict]]:
    """Parse + validate rows. Returns (rows, row_results)."""
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApiException(
            400,
            "IMPORT_ROW_INVALID",
            "The file must be UTF-8 encoded CSV.",
        ) from None
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    missing = [column for column in ("name", "category_code") if column not in headers]
    if missing:
        raise ApiException(
            400,
            "IMPORT_ROW_INVALID",
            f"The CSV is missing required columns: {', '.join(missing)}.",
            field_errors={"file": ["Download the template for the expected columns."]},
        )
    rows: list[dict] = []
    results: list[dict] = []
    for index, raw_row in enumerate(reader, start=2):  # row 1 = header
        if index - 1 > MAX_IMPORT_ROWS:
            results.append({"row": index, "status": "failed", "messages": ["Row limit exceeded."]})
            continue
        row: dict = {}
        messages: list[str] = []
        for column in TEMPLATE_COLUMNS:
            value = (raw_row.get(column) or "").strip()
            value, sanitized = _sanitize_cell(value)
            if sanitized:
                messages.append(f"{column}: formula-like value sanitized.")
            row[column] = value
        error_count = len(messages)
        _require(bool(row["name"]), "name is required.", messages)
        _require(bool(row["category_code"]), "category_code is required.", messages)
        if row["category_code"]:
            category_exists = Category.objects.filter(
                code__iexact=row["category_code"], active=True
            ).exists()
            _require(
                category_exists,
                f"category_code '{row['category_code']}' does not exist.",
                messages,
            )
        for column, model in (
            ("status_code", AssetStatus),
            ("condition_code", AssetCondition),
            ("department_code", Department),
            ("location_code", Location),
        ):
            if row[column]:
                exists = model.objects.filter(code__iexact=row[column], active=True).exists()
                _require(exists, f"{column} '{row[column]}' does not exist.", messages)
        for column in ("purchase_date", "warranty_start", "warranty_end"):
            if row[column]:
                try:
                    _parse_date(row[column])
                except ValueError:
                    messages.append(f"{column} must be YYYY-MM-DD.")
        if row["purchase_amount"]:
            try:
                Decimal(row["purchase_amount"])
            except InvalidOperation:
                messages.append("purchase_amount must be a decimal number.")
        rows.append(row)
        results.append(
            {
                "row": index,
                "status": "valid" if len(messages) == error_count else "failed",
                "messages": messages,
            }
        )
    return rows, results


def _row_to_asset_data(row: dict, refs: dict) -> dict:
    data: dict = {"name": row["name"]}
    data["category"] = refs["categories"][row["category_code"].lower()]
    if row["status_code"]:
        data["status"] = refs["statuses"][row["status_code"].lower()]
    if row["condition_code"]:
        data["condition"] = refs["conditions"][row["condition_code"].lower()]
    if row["department_code"]:
        data["department"] = refs["departments"][row["department_code"].lower()]
    if row["location_code"]:
        data["location"] = refs["locations"][row["location_code"].lower()]
    for column in ("serial_number", "manufacturer", "model", "acquisition_type"):
        if row[column]:
            data[column] = row[column]
    if row["purchase_date"]:
        data["purchase_date"] = _parse_date(row["purchase_date"])
    if row["purchase_amount"]:
        data["purchase_price"] = Decimal(row["purchase_amount"])
        data["purchase_currency"] = row["purchase_currency"] or "USD"
    if row["warranty_start"]:
        data["warranty_start"] = _parse_date(row["warranty_start"])
    if row["warranty_end"]:
        data["warranty_end"] = _parse_date(row["warranty_end"])
    if row["tag"]:
        data["tag"] = row["tag"]
    return data


def _references() -> dict:
    return {
        "categories": {c.code.lower(): c for c in Category.objects.filter(active=True)},
        "statuses": {s.code.lower(): s for s in AssetStatus.objects.filter(active=True)},
        "conditions": {c.code.lower(): c for c in AssetCondition.objects.filter(active=True)},
        "departments": {d.code.lower(): d for d in Department.objects.filter(active=True)},
        "locations": {loc.code.lower(): loc for loc in Location.objects.filter(active=True)},
    }


def run_import(job: ImportJob) -> ImportJob:
    """Commit a validated import. Safely repeatable: a completed job is
    returned unchanged (FR-018 idempotent commit)."""
    if job.status == ImportJob.Status.COMPLETED:
        return job
    with transaction.atomic():
        locked = ImportJob.objects.select_for_update().get(pk=job.pk)
        if locked.status == ImportJob.Status.COMPLETED:
            return locked
        file_path = Path(settings.MEDIA_ROOT) / locked.storage_key
        rows, results = validate_import_csv(file_path.read_bytes())
        refs = _references()
        actor = locked.requester
        created = updated = skipped = failed = 0
        for row, result in zip(rows, results, strict=True):
            if result["status"] != "valid":
                failed += 1
                continue
            data = _row_to_asset_data(row, refs)
            tag = row["tag"]
            existing = Asset.objects.filter(tag__iexact=tag).first() if tag else None
            try:
                if existing is not None:
                    if locked.policy == ImportJob.DuplicatePolicy.REJECT:
                        result["status"] = "failed"
                        result["messages"].append(f"tag '{tag}' already exists (policy: reject).")
                        failed += 1
                        continue
                    if locked.policy == ImportJob.DuplicatePolicy.SKIP:
                        result["status"] = "skipped"
                        result["messages"].append(f"tag '{tag}' already exists (policy: skip).")
                        skipped += 1
                        continue
                    update_data = {k: v for k, v in data.items() if k not in {"tag", "status"}}
                    update_asset(
                        actor=actor,
                        asset=existing,
                        data=update_data,
                        expected_version=existing.version,
                        correlation_id=locked.correlation_id,
                    )
                    result["status"] = "updated"
                    updated += 1
                else:
                    create_asset(actor=actor, data=data, correlation_id=locked.correlation_id)
                    result["status"] = "created"
                    created += 1
            except ApiException as exc:
                result["status"] = "failed"
                result["messages"].append(exc.message)
                failed += 1
        locked.total_rows = len(rows)
        locked.created_count = created
        locked.updated_count = updated
        locked.skipped_count = skipped
        locked.failed_count = failed
        locked.row_results = results
        locked.status = ImportJob.Status.COMPLETED
        locked.save()
        record_audit(
            actor=actor,
            action="import.commit",
            target=locked,
            after={
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
            },
            correlation_id=locked.correlation_id,
        )
    return locked


def _export_row(asset: Asset, include_finance: bool) -> list[str]:
    values: list[object] = [
        asset.tag,
        asset.name,
        asset.status.label if asset.status else "",
        asset.condition.label if asset.condition else "",
        asset.category.name if asset.category else "",
        asset.department.name if asset.department else "",
        asset.location.name if asset.location else "",
        str(asset.custodian) if asset.custodian else "",
        asset.serial_number,
        asset.manufacturer,
        asset.model,
        asset.acquisition_type,
        asset.purchase_date or "",
    ]
    if include_finance:
        values += [
            f"{asset.purchase_price:.2f}" if asset.purchase_price is not None else "",
            asset.purchase_currency,
        ]
    values += [
        asset.warranty_start or "",
        asset.warranty_end or "",
        asset.next_maintenance_due or "",
        asset.created_at.isoformat() if asset.created_at else "",
    ]
    return [sanitize_csv_value(value) for value in values]


def run_export(job: ExportJob, *, include_finance: bool) -> ExportJob:
    """Generate the export CSV. Respects scope + field permissions (FR-019)."""
    from apps.assets.filters import AssetFilter

    try:
        queryset = scope_assets(
            job.requester,
            Asset.objects.select_related(
                "status", "condition", "category", "department", "location", "custodian"
            ),
        )
        filterset = AssetFilter(job.filters, queryset=queryset)
        if not filterset.is_valid():
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "Export filters are invalid.",
            )
        queryset = filterset.qs.order_by("tag")
        columns = list(EXPORT_BASE_COLUMNS)
        if include_finance:
            columns = columns[:13] + EXPORT_FINANCE_COLUMNS + columns[13:]
        target_dir = Path(settings.MEDIA_ROOT) / "exports"
        os.makedirs(target_dir, exist_ok=True)
        storage_key = f"exports/{job.uuid}.csv"
        count = 0
        with open(target_dir / f"{job.uuid}.csv", "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            for asset in queryset.iterator():
                writer.writerow(_export_row(asset, include_finance))
                count += 1
        job.storage_key = storage_key
        job.row_count = count
        job.status = ExportJob.Status.COMPLETED
        job.save(update_fields=["storage_key", "row_count", "status", "updated_at"])
        record_audit(
            actor=job.requester,
            action="export.create",
            target=job,
            after={"row_count": count, "filters": job.filters},
            correlation_id=job.correlation_id,
        )
    except Exception as exc:  # noqa: BLE001 - job must record a support-safe error
        job.status = ExportJob.Status.FAILED
        job.error = str(exc)[:255]
        job.save(update_fields=["status", "error", "updated_at"])
    return job
