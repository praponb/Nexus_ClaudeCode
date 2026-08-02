from rest_framework import serializers

from apps.reference_data.models import (
    AssetCondition,
    AssetStatus,
    Category,
    CategoryAttributeDefinition,
    CostCenter,
    Department,
    Location,
    MaintenanceType,
    StatusTransitionRule,
    Supplier,
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["uuid", "name", "code", "description", "active", "created_at", "updated_at"]
        read_only_fields = ["uuid", "created_at", "updated_at"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            "uuid",
            "name",
            "code",
            "site",
            "building",
            "floor",
            "room",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "created_at", "updated_at"]


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = ["uuid", "name", "code", "description", "active", "created_at", "updated_at"]
        read_only_fields = ["uuid", "created_at", "updated_at"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "uuid",
            "name",
            "code",
            "description",
            "contact_email",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "created_at", "updated_at"]


class MaintenanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceType
        fields = ["uuid", "name", "code", "description", "active", "created_at", "updated_at"]
        read_only_fields = ["uuid", "created_at", "updated_at"]


class CategoryAttributeDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryAttributeDefinition
        fields = [
            "uuid",
            "key",
            "label",
            "field_type",
            "required",
            "options",
            "unique",
            "restricted",
        ]
        read_only_fields = ["uuid"]


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )
    attribute_definitions = CategoryAttributeDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            "uuid",
            "name",
            "code",
            "parent",
            "description",
            "active",
            "attribute_definitions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "created_at", "updated_at"]


class AssetStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetStatus
        fields = [
            "uuid",
            "code",
            "label",
            "icon",
            "semantic_treatment",
            "is_terminal",
            "active",
            "sort_order",
        ]
        read_only_fields = ["uuid"]


class AssetConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCondition
        fields = [
            "uuid",
            "code",
            "label",
            "icon",
            "semantic_treatment",
            "active",
            "sort_order",
        ]
        read_only_fields = ["uuid"]


class StatusTransitionRuleSerializer(serializers.ModelSerializer):
    from_status = serializers.SlugRelatedField(slug_field="code", read_only=True)
    to_status = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = StatusTransitionRule
        fields = [
            "uuid",
            "from_status",
            "to_status",
            "requires_reason",
            "requires_evidence",
            "requires_approval",
            "allowed_roles",
        ]
