from django.contrib import admin

from apps.assets.models import Asset, AssetTagSequence, LifecycleEvent


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("tag", "name", "category", "status", "department", "custodian")
    list_filter = ("status", "category", "record_status")
    search_fields = ("tag", "name", "serial_number")
    readonly_fields = ("uuid", "version")


@admin.register(LifecycleEvent)
class LifecycleEventAdmin(admin.ModelAdmin):
    list_display = ("asset", "event_type", "actor", "occurred_at")
    readonly_fields = ("asset", "event_type", "actor", "occurred_at", "summary", "details")

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(AssetTagSequence)
class AssetTagSequenceAdmin(admin.ModelAdmin):
    list_display = ("prefix", "next_value")
