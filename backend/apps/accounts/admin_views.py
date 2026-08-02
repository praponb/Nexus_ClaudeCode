"""User administration endpoints (FR-027; design §11.3 Admin group).

System administrators manage roles, scopes, and activation. The final active
system administrator can never be demoted or deactivated (409 LAST_ADMIN).
All changes are audited; secrets are never displayed.
"""

from django.db import transaction
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User, UserScope
from apps.audit.services import record_audit
from apps.core.exceptions import ApiException
from apps.core.permissions import IsSystemAdmin
from apps.reference_data.models import Department, Location

EDITABLE_FIELDS = {"display_name", "email", "role", "is_active", "department"}


class AdminUserSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    scopes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "uuid",
            "username",
            "display_name",
            "email",
            "role",
            "is_active",
            "department",
            "scopes",
            "last_login",
            "date_joined",
        ]
        read_only_fields = ["uuid", "username", "last_login", "date_joined"]

    def get_department(self, obj) -> dict | None:
        if obj.department is None:
            return None
        return {
            "uuid": str(obj.department.uuid),
            "code": obj.department.code,
            "name": obj.department.name,
        }

    def get_scopes(self, obj) -> list[dict]:
        rows = []
        for scope in obj.scopes.all():
            rows.append(
                {
                    "scope_type": scope.scope_type,
                    "department": (
                        {"uuid": str(scope.department.uuid), "name": scope.department.name}
                        if scope.department
                        else None
                    ),
                    "location": (
                        {"uuid": str(scope.location.uuid), "name": scope.location.name}
                        if scope.location
                        else None
                    ),
                    "business_unit": scope.business_unit,
                }
            )
        return rows


class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    serializer_class = AdminUserSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        queryset = User.objects.select_related("department").prefetch_related(
            "scopes__department", "scopes__location"
        )
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        params = self.request.query_params
        if params.get("role"):
            queryset = queryset.filter(role=params["role"])
        if params.get("is_active") is not None and params.get("is_active") != "":
            queryset = queryset.filter(
                is_active=params["is_active"].lower() in {"1", "true", "yes"}
            )
        return queryset

    def _active_admin_count(self, exclude: User) -> int:
        return (
            User.objects.filter(role=User.Role.SYSTEM_ADMIN, is_active=True)
            .exclude(pk=exclude.pk)
            .count()
        )

    def partial_update(self, request, *args, **kwargs) -> Response:
        target = self.get_object()
        data = request.data
        unknown = set(data) - EDITABLE_FIELDS - {"scopes"}
        if unknown:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                f"Fields not editable via user admin: {', '.join(sorted(unknown))}.",
                field_errors={field: ["Not editable here."] for field in sorted(unknown)},
            )
        new_role = data.get("role", target.role)
        if new_role not in {choice for choice, _ in User.Role.choices}:
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "Unknown role.",
                field_errors={"role": ["Provide a valid role."]},
            )
        new_active = data.get("is_active", target.is_active)
        if isinstance(new_active, str):
            new_active = new_active.lower() in {"1", "true", "yes"}
        losing_admin = (
            target.role == User.Role.SYSTEM_ADMIN and new_role != User.Role.SYSTEM_ADMIN
        ) or (target.is_active and not new_active and target.role == User.Role.SYSTEM_ADMIN)
        if losing_admin and self._active_admin_count(target) == 0:
            raise ApiException(
                409,
                "LAST_ADMIN",
                "The final active system administrator cannot be demoted or deactivated.",
            )
        with transaction.atomic():
            before = {
                "role": target.role,
                "is_active": target.is_active,
                "scopes": AdminUserSerializer(target).data["scopes"],
            }
            for field in EDITABLE_FIELDS & set(data):
                if field == "department":
                    raw = data["department"]
                    target.department = (
                        Department.objects.filter(uuid=str(raw)).first() if raw else None
                    )
                elif field == "is_active":
                    target.is_active = bool(new_active)
                else:
                    setattr(target, field, data[field])
            target.save()
            if "scopes" in data:
                self._replace_scopes(target, data["scopes"])
            record_audit(
                actor=request.user,
                action="admin.user.update",
                target=target,
                before=before,
                after={
                    "role": target.role,
                    "is_active": target.is_active,
                    "scopes": AdminUserSerializer(target).data["scopes"],
                },
                correlation_id=getattr(request, "correlation_id", None),
            )
        return Response(self.get_serializer(target).data)

    def _replace_scopes(self, target: User, scopes) -> None:
        if not isinstance(scopes, list):
            raise ApiException(
                400,
                "VALIDATION_FAILED",
                "scopes must be a list.",
                field_errors={"scopes": ["Provide a list of scope objects."]},
            )
        target.scopes.all().delete()
        for entry in scopes:
            if not isinstance(entry, dict):
                continue
            scope_type = entry.get("scope_type")
            if scope_type not in {choice for choice, _ in UserScope.ScopeType.choices}:
                raise ApiException(
                    400,
                    "VALIDATION_FAILED",
                    "Unknown scope type.",
                    field_errors={
                        "scopes": ["scope_type must be department|location|business_unit."]
                    },
                )
            department = None
            location = None
            if scope_type == "department":
                raw_department = entry.get("department")
                department = (
                    Department.objects.filter(uuid=str(raw_department)).first()
                    if raw_department
                    else None
                )
                if department is None:
                    raise ApiException(
                        400,
                        "VALIDATION_FAILED",
                        "Unknown department.",
                        field_errors={"scopes": ["Department not found."]},
                    )
            if scope_type == "location":
                raw_location = entry.get("location")
                location = (
                    Location.objects.filter(uuid=str(raw_location)).first()
                    if raw_location
                    else None
                )
                if location is None:
                    raise ApiException(
                        400,
                        "VALIDATION_FAILED",
                        "Unknown location.",
                        field_errors={"scopes": ["Location not found."]},
                    )
            UserScope.objects.create(
                user=target,
                scope_type=scope_type,
                department=department,
                location=location,
                business_unit=(
                    entry.get("business_unit", "") if scope_type == "business_unit" else ""
                ),
            )
