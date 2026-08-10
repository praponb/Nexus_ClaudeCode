import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bulk.models import ExportJob, ImportJob
from apps.bulk.serializers import ExportJobSerializer, ImportJobSerializer
from apps.bulk.services import run_export, run_import, template_csv, validate_import_csv
from apps.bulk.tasks import process_export_job, process_import_job
from apps.core import capabilities
from apps.core.exceptions import ApiException
from apps.core.idempotency import idempotency_key_from, run_idempotent
from apps.core.permissions import CanEditAsset
from apps.core.throttling import ScopedSimpleRateThrottle

MAX_UPLOAD_BYTES = 32 * 1024 * 1024


class ImportExportThrottle(ScopedSimpleRateThrottle):
    """Rate limit on heavy CSV import/export operations (NFR-007)."""

    scope = "import_export"

    def allow_request(self, request, view):
        if self.rate is None:
            return True
        return super().allow_request(request, view)


class ImportTemplateView(APIView):
    """CSV template download (FR-018)."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        return Response({"columns": template_csv().strip().split(","), "csv": template_csv()})


class ImportJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ImportJobSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = ImportJob.objects.select_related("requester")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        if capabilities.is_global_reader(self.request.user):
            return queryset
        return queryset.filter(requester=self.request.user)

    def get_permissions(self):
        if self.action in {"create", "commit"}:
            return [IsAuthenticated(), CanEditAsset()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action in {"create", "commit"}:
            return [ImportExportThrottle()]
        return super().get_throttles()

    def create(self, request, *args, **kwargs) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "A CSV file is required.",
                field_errors={"file": ["Upload a UTF-8 CSV file."]},
            )
        if upload.size > MAX_UPLOAD_BYTES:
            raise ApiException(413, "UPLOAD_TOO_LARGE", "The uploaded file is too large.")
        policy = str(request.data.get("policy", ImportJob.DuplicatePolicy.SKIP) or "skip")
        if policy not in {choice for choice, _ in ImportJob.DuplicatePolicy.choices}:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "Unknown duplicate policy.",
                field_errors={"policy": ["Must be reject, skip, or update."]},
            )
        file_bytes = upload.read()
        rows, results = validate_import_csv(file_bytes)
        target_dir = Path(settings.MEDIA_ROOT) / "imports"
        os.makedirs(target_dir, exist_ok=True)
        job = ImportJob.objects.create(
            requester=request.user,
            original_filename=os.path.basename(upload.name or "import.csv"),
            storage_key="",
            policy=policy,
            status=ImportJob.Status.VALIDATED,
            total_rows=len(rows),
            failed_count=sum(1 for result in results if result["status"] == "failed"),
            row_results=results,
            correlation_id=getattr(request, "correlation_id", None),
        )
        job.storage_key = f"imports/{job.uuid}.csv"
        job.save(update_fields=["storage_key", "updated_at"])
        (target_dir / f"{job.uuid}.csv").write_bytes(file_bytes)
        return Response(self.get_serializer(job).data, status=201)

    @action(detail=True, methods=["post"], url_path="commit")
    def commit(self, request, uuid=None) -> Response:
        job = self.get_object()
        if job.requester != request.user and not capabilities.is_system_admin(request.user):
            raise ApiException(
                403, "PERMISSION_DENIED", "Only the requester can commit this import."
            )

        def handler() -> tuple[int, dict]:
            process_import_job.delay(job.pk)
            job.refresh_from_db()
            return 200, self.get_serializer(job).data

        key = idempotency_key_from(request)
        if key is None:
            status, body = handler()
            return Response(body, status=status)
        status, body, _ = run_idempotent(
            user=request.user,
            endpoint=f"POST {request.path}",
            key=key,
            request_payload={},
            handler=handler,
        )
        return Response(body, status=status)

    @action(detail=True, methods=["get"], url_path="result")
    def result(self, request, uuid=None) -> Response:
        job = self.get_object()
        return Response(
            {
                "uuid": str(job.uuid),
                "status": job.status,
                "total_rows": job.total_rows,
                "created": job.created_count,
                "updated": job.updated_count,
                "skipped": job.skipped_count,
                "failed": job.failed_count,
                "rows": job.row_results,
            }
        )


class ExportJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ExportJobSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = ExportJob.objects.select_related("requester")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        if capabilities.is_system_admin(self.request.user):
            return queryset
        return queryset.filter(requester=self.request.user)

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action == "create":
            return [ImportExportThrottle()]
        return super().get_throttles()

    def create(self, request, *args, **kwargs) -> Response:
        filters = request.data.get("filters") or {}
        if not isinstance(filters, dict):
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "Filters must be a JSON object.",
                field_errors={"filters": ["Provide an object of asset-list filter values."]},
            )
        job = ExportJob.objects.create(
            requester=request.user,
            filters=filters,
            correlation_id=getattr(request, "correlation_id", None),
        )
        include_finance = capabilities.can_view_finance(request.user)
        process_export_job.delay(job.pk, include_finance)
        job.refresh_from_db()
        return Response(self.get_serializer(job).data, status=201)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, uuid=None) -> FileResponse:
        job = self.get_object()
        if job.requester != request.user and not capabilities.is_system_admin(request.user):
            raise ApiException(
                403, "PERMISSION_DENIED", "Only the requester can download this export."
            )
        if job.status != ExportJob.Status.COMPLETED or not job.storage_key:
            raise ApiException(409, "EXPORT_NOT_READY", "This export is not ready for download.")
        file_path = Path(settings.MEDIA_ROOT) / job.storage_key
        if not file_path.exists():
            raise ApiException(404, "NOT_FOUND", "The export file has expired.")
        return FileResponse(
            open(file_path, "rb"),
            content_type="text/csv; charset=utf-8",
            as_attachment=True,
            filename=f"asset-export-{job.uuid}.csv",
        )


# run_import/run_export imported for the eager fallback used in tests without
# a broker; the task functions already call them.
_ = (run_import, run_export)
