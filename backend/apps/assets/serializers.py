from typing import Any

from rest_framework import serializers

from apps.accounts.models import User
from apps.assets.fields import MoneyField, UUIDRelatedField
from apps.assets.models import Asset
from apps.core import capabilities
from apps.reference_data.models import (
    AssetCondition,
    AssetStatus,
    Category,
    Department,
    Location,
    Supplier,
)

FINANCE_FIELDS = ("purchase", "po_reference", "invoice_reference", "lease_reference", "lease_end")

OPERATIONAL_REQUIRED = (
    ("condition", "Condition"),
    ("department", "Department"),
    ("location", "Location"),
    ("acquisition_type", "Acquisition type"),
)


class AssetSerializer(serializers.ModelSerializer):
    # Optional on write: when blank the service generates the next tag from the
    # per-prefix sequence (FR-003). Immutable once set (validated below).
    tag = serializers.CharField(required=False, allow_blank=True, max_length=64)
    category = UUIDRelatedField(queryset=Category.objects.all(), repr_fields=("code", "name"))
    status = UUIDRelatedField(
        queryset=AssetStatus.objects.all(),
        repr_fields=("code", "label", "icon", "semantic_treatment", "is_terminal"),
        required=False,
        allow_null=True,
    )
    condition = UUIDRelatedField(
        queryset=AssetCondition.objects.all(),
        repr_fields=("code", "label", "icon", "semantic_treatment"),
        required=False,
        allow_null=True,
    )
    department = UUIDRelatedField(
        queryset=Department.objects.all(),
        repr_fields=("code", "name"),
        required=False,
        allow_null=True,
    )
    location = UUIDRelatedField(
        queryset=Location.objects.all(),
        repr_fields=("code", "name"),
        required=False,
        allow_null=True,
    )
    custodian = UUIDRelatedField(
        queryset=User.objects.all(),
        repr_fields=("username", "display_name"),
        required=False,
        allow_null=True,
    )
    supplier = UUIDRelatedField(
        queryset=Supplier.objects.all(),
        repr_fields=("code", "name"),
        required=False,
        allow_null=True,
    )
    parent_asset = UUIDRelatedField(
        queryset=Asset.objects.all(),
        repr_fields=("tag", "name"),
        required=False,
        allow_null=True,
    )
    purchase = MoneyField(required=False, allow_null=True)

    class Meta:
        model = Asset
        fields = [
            "uuid",
            "tag",
            "name",
            "description",
            "category",
            "status",
            "condition",
            "department",
            "location",
            "custodian",
            "serial_number",
            "manufacturer",
            "brand",
            "model",
            "parent_asset",
            "barcode_value",
            "external_ids",
            "acquisition_type",
            "purchase_date",
            "purchase",
            "po_reference",
            "invoice_reference",
            "supplier",
            "lease_reference",
            "lease_end",
            "warranty_provider",
            "warranty_start",
            "warranty_end",
            "last_maintenance_date",
            "next_maintenance_due",
            "maintenance_interval_months",
            "hostname",
            "mac_address",
            "ip_address",
            "os",
            "specs",
            "imei",
            "license_id",
            "category_attributes",
            "received_date",
            "in_service_date",
            "useful_life_end",
            "retirement_date",
            "disposal_date",
            "disposal_method",
            "disposal_reason",
            "data_quality_status",
            "legal_hold",
            "record_status",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "useful_life_end",
            "retirement_date",
            "disposal_date",
            "disposal_method",
            "disposal_reason",
            "data_quality_status",
            "record_status",
            "version",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated and capabilities.can_view_finance(user)):
            # Field-level finance restriction (BR-007): hidden entirely.
            for field_name in FINANCE_FIELDS:
                self.fields.pop(field_name, None)

    def validate(self, attrs: dict) -> dict:
        if self.instance is not None and "tag" in attrs and attrs["tag"] != self.instance.tag:
            raise serializers.ValidationError({"tag": ["The asset tag is immutable."]})

        if "purchase" in attrs:
            purchase = attrs.pop("purchase")
            if purchase is None:
                attrs["purchase_price"] = None
                attrs["purchase_currency"] = ""
            else:
                attrs.update(purchase)

        status = attrs.get("status") or (self.instance.status if self.instance else None)
        is_draft = status is not None and status.code == "draft"
        errors: dict[str, Any] = {}
        if not is_draft:
            for field_name, label in OPERATIONAL_REQUIRED:
                if field_name in attrs:
                    current = attrs[field_name]
                elif self.instance is not None:
                    current = getattr(self.instance, field_name)
                else:
                    current = None
                if current in (None, ""):
                    errors[field_name] = [f"{label} is required unless saving as Draft."]

        category = attrs.get("category") or (self.instance.category if self.instance else None)
        if category is not None:
            if "category_attributes" in attrs:
                provided = attrs["category_attributes"] or {}
            elif self.instance is not None:
                provided = self.instance.category_attributes or {}
            else:
                provided = {}
            attribute_errors: dict[str, list[str]] = {}
            for definition in category.attribute_definitions.filter(required=True):
                value = provided.get(definition.key)
                if value in (None, "", []):
                    attribute_errors[definition.key] = [
                        f"'{definition.label}' is required for category '{category.name}'."
                    ]
            if attribute_errors:
                errors["category_attributes"] = attribute_errors

        if errors:
            raise serializers.ValidationError(errors)
        return attrs
