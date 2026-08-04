import logging
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.approvals.models import ApprovalRequest
from apps.approvals.serializers import ApprovalSerializer
from apps.assets import services
from apps.assets.attachments import remove_stored, store_upload, validate_upload
from apps.assets.filters import AssetFilter
from apps.assets.models import Asset, Attachment, Note
from apps.assets.serializers import AssetSerializer
from apps.assignments import services as workflow
from apps.assignments.serializers import (
    AssignSerializer,
    CheckoutSerializer,
    DisposeSerializer,
    ExceptionReportSerializer,
    ReopenSerializer,
    ReserveSerializer,
    RetireSerializer,
    ReturnSerializer,
    TransferSerializer,
    assignment_summary,
    reservation_summary,
    transfer_summary,
)
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.core.idempotency import idempotency_key_from, run_idempotent
from apps.core.permissions import CanCreateAsset, CanEditAsset, IsSystemAdmin, scope_assets

logger = logging.getLogger(__name__)


def _attachment_summary(attachment: Attachment) -> dict:
    return {
        "uuid": str(attachment.uuid),
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "size": attachment.size,
        "purpose": attachment.purpose,
        "scan_status": attachment.scan_status,
        "uploaded_by": (str(attachment.uploaded_by) if attachment.uploaded_by else None),
        "created_at": attachment.created_at,
    }


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_class = AssetFilter
    # Must match what the UI promises the register filter covers ("tag, serial,
    # name, model, custodian, or location") and stay aligned with the global
    # search endpoint below, so both entry points find the same assets.
    search_fields = [
        "tag",
        "name",
        "serial_number",
        "manufacturer",
        "model",
        "custodian__username",
        "custodian__display_name",
        "location__name",
    ]
    ordering_fields = ["tag", "name", "created_at", "updated_at"]
    ordering = ["tag"]

    def get_queryset(self):
        queryset = Asset.objects.select_related(
            "category",
            "status",
            "condition",
            "department",
            "location",
            "custodian",
            "supplier",
            "parent_asset",
        )
        # Scope filtering is the authorization boundary (FR-002); out-of-scope
        # objects resolve to 404 so existence is not leaked.
        return scope_assets(self.request.user, queryset)

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanCreateAsset()]
        if self.action in {
            "partial_update",
            "assign",
            "transfer",
            "return_asset",
            "reserve",
            "checkout",
            "retire",
            "dispose",
            "upload_attachment",
            "delete_attachment",
        }:
            return [IsAuthenticated(), CanEditAsset()]
        if self.action == "reopen":
            return [IsAuthenticated(), IsSystemAdmin()]
        # report_exception / notes / attachments (GET): any authenticated user
        # with asset visibility (employees act on their own assets, spec §5).
        return [IsAuthenticated()]

    def _respond(self, request, handler):
        """Run a workflow handler with Idempotency-Key semantics (D-08)."""
        key = idempotency_key_from(request)
        if key is None:
            status, body = handler()
            return Response(body, status=status)
        status, body, _replayed = run_idempotent(
            user=request.user,
            endpoint=f"POST {request.path}",
            key=key,
            request_payload=request.data,
            handler=handler,
        )
        return Response(body, status=status)

    def create(self, request, *args, **kwargs) -> Response:
        def handler() -> tuple[int, dict]:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            asset = services.create_asset(
                actor=request.user,
                data=data,
                correlation_id=getattr(request, "correlation_id", None),
            )
            warnings = services.find_duplicate_warnings(
                serial_number=asset.serial_number,
                manufacturer=asset.manufacturer,
                model=asset.model,
                exclude_uuid=asset.uuid,
            )
            output = self.get_serializer(asset).data
            return 201, {"asset": output, "warnings": warnings}

        return self._respond(request, handler)

    def partial_update(self, request, *args, **kwargs) -> Response:
        asset = self.get_object()
        raw_version = request.headers.get("If-Match") or request.data.get("version")
        if raw_version in (None, ""):
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "A current asset version is required for updates.",
                field_errors={
                    "version": ["Send the asset version in the request body or If-Match header."]
                },
            )
        try:
            expected_version = int(str(raw_version).strip('"'))
        except (TypeError, ValueError):
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "The supplied version is invalid.",
                field_errors={"version": ["Version must be an integer."]},
            ) from None
        serializer = self.get_serializer(asset, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        asset = services.update_asset(
            actor=request.user,
            asset=asset,
            data=dict(serializer.validated_data),
            expected_version=expected_version,
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(self.get_serializer(asset).data)

    def destroy(self, request, *args, **kwargs) -> Response:
        # Business records are never hard-deleted via the API (BR-003/FR-030).
        raise ApiException(
            405, "METHOD_NOT_ALLOWED", "Assets cannot be deleted; retire or archive them."
        )

    # -- Workflow endpoints (design section 11.3) ----------------------------

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = AssignSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            assignment = workflow.assign_asset(
                actor=request.user,
                asset=asset,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            return 200, {
                "asset": self.get_serializer(Asset.objects.get(pk=asset.pk)).data,
                "assignment": assignment_summary(assignment),
            }

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="return")
    def return_asset(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = ReturnSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            assignment = workflow.return_asset(
                actor=request.user,
                asset=asset,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            return 200, {
                "asset": self.get_serializer(Asset.objects.get(pk=asset.pk)).data,
                "assignment": assignment_summary(assignment),
            }

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = TransferSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            confirm = data.pop("confirm", False)
            if confirm:
                result = workflow.confirm_transfer(
                    actor=request.user,
                    asset=asset,
                    correlation_id=getattr(request, "correlation_id", None),
                )
            else:
                result = workflow.transfer_asset(
                    actor=request.user,
                    asset=asset,
                    correlation_id=getattr(request, "correlation_id", None),
                    **data,
                )
            if isinstance(result, ApprovalRequest):
                # FR-024: transfer held for approval; nothing mutated yet.
                return 202, {"approval": ApprovalSerializer(result).data}
            return 200, {
                "asset": self.get_serializer(Asset.objects.get(pk=asset.pk)).data,
                "transfer": transfer_summary(result),
            }

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="reserve")
    def reserve(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = ReserveSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            reservation = workflow.reserve_asset(
                actor=request.user,
                asset=asset,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            return 201, {"reservation": reservation_summary(reservation)}

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="checkout")
    def checkout(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = CheckoutSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            assignment = workflow.checkout_reservation(
                actor=request.user,
                asset=asset,
                reservation_uuid=serializer.validated_data["reservation"],
                correlation_id=getattr(request, "correlation_id", None),
            )
            return 200, {
                "asset": self.get_serializer(Asset.objects.get(pk=asset.pk)).data,
                "assignment": assignment_summary(assignment),
            }

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="retire")
    def retire(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = RetireSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            retired = workflow.retire_asset(
                actor=request.user,
                asset=asset,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            return 200, {"asset": self.get_serializer(retired).data}

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="dispose")
    def dispose(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = DisposeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            result = workflow.dispose_asset(
                actor=request.user,
                asset=asset,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            if isinstance(result, ApprovalRequest):
                # FR-024: disposal held for approval; nothing mutated yet.
                return 202, {"approval": ApprovalSerializer(result).data}
            return 200, {"asset": self.get_serializer(result).data}

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="reopen")
    def reopen(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = ReopenSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            reopened = workflow.reopen_asset(
                actor=request.user,
                asset=asset,
                correlation_id=getattr(request, "correlation_id", None),
                **serializer.validated_data,
            )
            return 200, {"asset": self.get_serializer(reopened).data}

        return self._respond(request, handler)

    @action(detail=True, methods=["post"], url_path="report-exception")
    def report_exception(self, request, uuid=None) -> Response:
        asset = self.get_object()

        def handler() -> tuple[int, dict]:
            serializer = ExceptionReportSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            if data.pop("resolve", False):
                report = workflow.resolve_exception(
                    actor=request.user,
                    asset=asset,
                    resolution=data.get("resolution", ""),
                    correlation_id=getattr(request, "correlation_id", None),
                )
            else:
                report = workflow.report_exception(
                    actor=request.user,
                    asset=asset,
                    report_type=data["report_type"],
                    description=data.get("description", ""),
                    evidence=data.get("evidence", ""),
                    correlation_id=getattr(request, "correlation_id", None),
                )
            return 200, {
                "asset": self.get_serializer(Asset.objects.get(pk=asset.pk)).data,
                "exception_report": {
                    "uuid": str(report.uuid),
                    "report_type": report.report_type,
                    "status": report.status,
                },
            }

        return self._respond(request, handler)

    # -- Attachments, notes, activity, label ---------------------------------

    @action(detail=True, methods=["get"], url_path="attachments")
    def attachments(self, request, uuid=None) -> Response:
        asset = self.get_object()
        rows = [_attachment_summary(item) for item in asset.attachments.all()]
        return Response({"results": rows})

    @attachments.mapping.post
    def upload_attachment(self, request, uuid=None) -> Response:
        asset = self.get_object()
        upload = request.FILES.get("file")
        if upload is None:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "A file is required.",
                field_errors={"file": ["Attach a file to upload."]},
            )
        content = upload.read()
        filename, extension = validate_upload(filename=upload.name or "", content=content)
        storage_key = store_upload(asset.uuid, content, extension)
        attachment = Attachment.objects.create(
            asset=asset,
            filename=filename,
            content_type=upload.content_type or "application/octet-stream",
            size=len(content),
            storage_key=storage_key,
            uploaded_by=request.user,
            purpose=str(request.data.get("purpose", "") or "")[:64],
        )
        record_audit(
            actor=request.user,
            action="attachment.upload",
            target=asset,
            after={"attachment_uuid": str(attachment.uuid), "filename": filename},
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(_attachment_summary(attachment), status=201)

    def _get_attachment(self, asset: Asset, attachment_uuid: str) -> Attachment:
        attachment = asset.attachments.filter(uuid=attachment_uuid).first()
        if attachment is None:
            raise ApiException(404, "NOT_FOUND", "The requested resource was not found.")
        return attachment

    @action(
        detail=True,
        methods=["get"],
        url_path=r"attachments/(?P<attachment_uuid>[^/.]+)/download",
    )
    def download_attachment(self, request, uuid=None, attachment_uuid=None) -> FileResponse:
        asset = self.get_object()
        attachment = self._get_attachment(asset, attachment_uuid)
        file_path = Path(settings.MEDIA_ROOT) / attachment.storage_key
        if not file_path.exists():
            raise ApiException(404, "NOT_FOUND", "The file is no longer available.")
        record_audit(
            actor=request.user,
            action="attachment.download",
            target=asset,
            after={"attachment_uuid": str(attachment.uuid), "filename": attachment.filename},
            correlation_id=getattr(request, "correlation_id", None),
        )
        return FileResponse(
            open(file_path, "rb"),
            content_type=attachment.content_type,
            as_attachment=True,
            filename=attachment.filename,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"attachments/(?P<attachment_uuid>[^/.]+)",
    )
    def delete_attachment(self, request, uuid=None, attachment_uuid=None) -> Response:
        asset = self.get_object()
        attachment = self._get_attachment(asset, attachment_uuid)
        summary = _attachment_summary(attachment)
        remove_stored(attachment.storage_key)
        attachment.delete()
        record_audit(
            actor=request.user,
            action="attachment.remove",
            target=asset,
            before={"attachment_uuid": summary["uuid"], "filename": summary["filename"]},
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(status=204)

    @action(detail=True, methods=["get", "post"], url_path="notes")
    def notes(self, request, uuid=None) -> Response:
        asset = self.get_object()
        if request.method == "GET":
            rows = [
                {
                    "uuid": str(note.uuid),
                    "body": note.body,
                    "author": str(note.author) if note.author else None,
                    "created_at": note.created_at,
                }
                for note in asset.notes.all()[:100]
            ]
            return Response({"results": rows})
        body = str(request.data.get("body", "") or "").strip()
        if not body:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "A note body is required.",
                field_errors={"body": ["This field is required."]},
            )
        note = Note.objects.create(asset=asset, author=request.user, body=body)
        record_audit(
            actor=request.user,
            action="note.create",
            target=asset,
            after={"note_uuid": str(note.uuid)},
            correlation_id=getattr(request, "correlation_id", None),
        )
        return Response(
            {
                "uuid": str(note.uuid),
                "body": note.body,
                "author": str(note.author) if note.author else None,
                "created_at": note.created_at,
            },
            status=201,
        )

    @action(detail=True, methods=["get"], url_path="activity")
    def activity(self, request, uuid=None) -> Response:
        """FR-029: unified reverse-chronological feed (lifecycle, notes, audit)."""
        asset = self.get_object()
        items: list[dict] = []
        for event in asset.lifecycle_events.all()[:200]:
            items.append(
                {
                    "type": "lifecycle",
                    "occurred_at": event.occurred_at,
                    "actor": str(event.actor) if event.actor else (event.actor_label or None),
                    "event_type": event.event_type,
                    "summary": event.summary,
                    "details": event.details,
                }
            )
        for note in asset.notes.all()[:100]:
            items.append(
                {
                    "type": "note",
                    "occurred_at": note.created_at,
                    "actor": str(note.author) if note.author else None,
                    "event_type": "note",
                    "summary": note.body,
                    "details": {},
                }
            )
        audit_events = AuditEvent.objects.filter(
            target_type="assets.asset", target_uuid=asset.uuid
        )[:200]
        for event in audit_events:
            items.append(
                {
                    "type": "audit",
                    "occurred_at": event.created_at,
                    "actor": str(event.actor) if event.actor else None,
                    "event_type": event.action,
                    "summary": event.action,
                    "details": {"before": event.before, "after": event.after},
                }
            )
        items.sort(key=lambda item: item["occurred_at"], reverse=True)
        return Response({"results": items[:100]})

    @action(detail=True, methods=["get"], url_path="label")
    def label(self, request, uuid=None) -> Response:
        """FR-017/D-14: QR label payload (SVG) encoding the scan deep link."""
        import qrcode
        import qrcode.image.svg

        asset = self.get_object()
        url = f"{settings.APP_BASE_URL}/scan?tag={asset.tag}"
        image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
        svg = image.to_string().decode("utf-8")
        return Response(
            {
                "tag": asset.tag,
                "name": asset.name,
                "url": url,
                "svg": svg,
                "label": {"width_mm": 50, "height_mm": 25},
            }
        )

    # -- Existing read endpoints --------------------------------------------

    @action(detail=False, methods=["post"], url_path="check-duplicates")
    def check_duplicates(self, request) -> Response:
        warnings = services.find_duplicate_warnings(
            serial_number=str(request.data.get("serial_number", "") or ""),
            manufacturer=str(request.data.get("manufacturer", "") or ""),
            model=str(request.data.get("model", "") or ""),
        )
        return Response({"warnings": warnings})

    @action(detail=True, methods=["post"], url_path="check-duplicates")
    def check_duplicates_detail(self, request, uuid=None) -> Response:
        asset = self.get_object()
        warnings = services.find_duplicate_warnings(
            serial_number=str(request.data.get("serial_number") or asset.serial_number or ""),
            manufacturer=str(request.data.get("manufacturer") or asset.manufacturer or ""),
            model=str(request.data.get("model") or asset.model or ""),
            exclude_uuid=asset.uuid,
        )
        return Response({"warnings": warnings})

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, uuid=None) -> Response:
        asset = self.get_object()
        events: list[dict] = []
        for event in asset.lifecycle_events.all()[:200]:
            events.append(
                {
                    "type": "lifecycle",
                    "occurred_at": event.occurred_at,
                    "actor": str(event.actor) if event.actor else (event.actor_label or None),
                    "event_type": event.event_type,
                    "summary": event.summary,
                    "details": event.details,
                    "correlation_id": (str(event.correlation_id) if event.correlation_id else None),
                }
            )
        audit_events = AuditEvent.objects.filter(
            target_type="assets.asset", target_uuid=asset.uuid
        )[:200]
        for event in audit_events:
            events.append(
                {
                    "type": "audit",
                    "occurred_at": event.created_at,
                    "actor": str(event.actor) if event.actor else None,
                    "event_type": event.action,
                    "summary": event.action,
                    "details": {"before": event.before, "after": event.after},
                    "correlation_id": (str(event.correlation_id) if event.correlation_id else None),
                }
            )
        events.sort(key=lambda item: item["occurred_at"], reverse=True)
        return Response({"results": events[:100]})


def _search_result(asset: Asset, match: str) -> dict:
    status = asset.status
    return {
        "uuid": str(asset.uuid),
        "tag": asset.tag,
        "name": asset.name,
        "status": {
            "code": status.code,
            "label": status.label,
            "icon": status.icon,
            "semantic_treatment": status.semantic_treatment,
        },
        "category": asset.category.name if asset.category else None,
        "location": asset.location.name if asset.location else None,
        "custodian": str(asset.custodian) if asset.custodian else None,
        "match": match,
    }


class AssetSearchView(APIView):
    """Global search: exact tag match first, then partial matches (FR-005)."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        query = str(request.query_params.get("q", "") or "").strip()
        if not query:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "A search query is required.",
                field_errors={"q": ["Provide a search term."]},
            )
        base = scope_assets(
            request.user,
            Asset.objects.select_related("status", "category", "location", "custodian"),
        )
        exact = list(base.filter(tag__iexact=query)[:5])
        partial = base.filter(
            Q(tag__icontains=query)
            | Q(name__icontains=query)
            | Q(serial_number__icontains=query)
            | Q(manufacturer__icontains=query)
            | Q(model__icontains=query)
            | Q(custodian__username__icontains=query)
            | Q(custodian__display_name__icontains=query)
            | Q(location__name__icontains=query)
        ).exclude(pk__in=[asset.pk for asset in exact])
        results = [_search_result(asset, "exact") for asset in exact]
        results += [_search_result(asset, "partial") for asset in partial[:10]]
        return Response({"results": results[:10]})
