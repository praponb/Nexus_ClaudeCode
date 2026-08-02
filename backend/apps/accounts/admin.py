from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User, UserScope


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "display_name", "role", "department", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = tuple(DjangoUserAdmin.fieldsets or ()) + (
        (
            "Asset inventory",
            {"fields": ("uuid", "role", "display_name", "department", "locale", "timezone")},
        ),
    )
    readonly_fields = ("uuid",)


@admin.register(UserScope)
class UserScopeAdmin(admin.ModelAdmin):
    list_display = ("user", "scope_type", "department", "location", "business_unit")
