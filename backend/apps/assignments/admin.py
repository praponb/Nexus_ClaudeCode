from django.contrib import admin

from apps.assignments.models import Assignment


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("asset", "custodian", "department", "assigned_at", "returned_at", "status")
    list_filter = ("status",)
