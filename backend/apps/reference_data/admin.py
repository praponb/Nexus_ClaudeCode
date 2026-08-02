from django.contrib import admin

from apps.reference_data.models import (
    AssetCondition,
    AssetStatus,
    Category,
    CategoryAttributeDefinition,
    CostCenter,
    Department,
    Location,
    StatusTransitionRule,
    Supplier,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "active")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "site", "building", "active")


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "active")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "active")


class AttributeDefinitionInline(admin.TabularInline):
    model = CategoryAttributeDefinition
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "active")
    inlines = [AttributeDefinitionInline]


@admin.register(AssetStatus)
class AssetStatusAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "is_terminal", "active", "sort_order")


@admin.register(AssetCondition)
class AssetConditionAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "active", "sort_order")


@admin.register(StatusTransitionRule)
class StatusTransitionRuleAdmin(admin.ModelAdmin):
    list_display = ("from_status", "to_status", "requires_approval")
