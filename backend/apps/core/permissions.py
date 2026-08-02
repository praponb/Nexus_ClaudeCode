"""DRF permission classes and organizational-scope filtering (FR-002)."""

from django.db.models import Q, QuerySet
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.core import capabilities


class CanCreateAsset(BasePermission):
    message = "You do not have permission to create assets."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and capabilities.can_write_assets(user))


class CanEditAsset(BasePermission):
    message = "You do not have permission to edit assets."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and capabilities.can_write_assets(user))


class IsManagerOrAdmin(BasePermission):
    """Asset managers and system administrators (stocktake/session control)."""

    message = "This action requires an asset manager or system administrator role."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and capabilities.user_role(user) in {"system_admin", "asset_manager"}
        )


class IsSystemAdmin(BasePermission):
    """System administrators only (elevated actions, e.g. reopening disposal)."""

    message = "This action requires a system administrator role."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and capabilities.is_system_admin(user))


class ReferenceDataPermission(BasePermission):
    """Read: any authenticated user. Write: system administrators only (FR-026)."""

    message = "Only system administrators may modify reference data."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return capabilities.is_system_admin(user)


def scope_assets(user, queryset: QuerySet) -> QuerySet:
    """Restrict an asset queryset to the user's organizational scope.

    Global readers (admin, asset manager, auditor) see everything. Scoped roles
    (operator, department manager, employee) see assets they custody or assets
    in their department/location scopes. Unknown roles see nothing.
    """
    if capabilities.is_global_reader(user):
        return queryset
    if capabilities.user_role(user) in {
        "operator",
        "department_manager",
        "employee",
    }:
        department_ids = [
            scope.department_id
            for scope in user.scopes.all()
            if scope.scope_type == "department" and scope.department_id
        ]
        location_ids = [
            scope.location_id
            for scope in user.scopes.all()
            if scope.scope_type == "location" and scope.location_id
        ]
        predicate = Q(custodian=user)
        if department_ids:
            predicate |= Q(department_id__in=department_ids)
        if location_ids:
            predicate |= Q(location_id__in=location_ids)
        return queryset.filter(predicate).distinct()
    return queryset.none()
