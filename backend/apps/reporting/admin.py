from django.contrib import admin

from apps.reporting.models import SavedView


@admin.register(SavedView)
class SavedViewAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "shared", "is_default")
