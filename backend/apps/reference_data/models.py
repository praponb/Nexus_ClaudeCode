from django.db import models

from apps.core.models import CoreModel


class Department(CoreModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Location(CoreModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, unique=True)
    site = models.CharField(max_length=120, blank=True, default="")
    building = models.CharField(max_length=64, blank=True, default="")
    floor = models.CharField(max_length=64, blank=True, default="")
    room = models.CharField(max_length=64, blank=True, default="")
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class CostCenter(CoreModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Supplier(CoreModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Category(CoreModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class CategoryAttributeDefinition(CoreModel):
    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        LONGTEXT = "longtext", "Long text"
        NUMBER = "number", "Number"
        DECIMAL = "decimal", "Decimal"
        CURRENCY = "currency", "Currency"
        DATE = "date", "Date"
        DATETIME = "datetime", "Date/time"
        BOOL = "bool", "Boolean"
        CHOICE = "choice", "Choice"
        MULTICHOICE = "multichoice", "Multiple choice"
        REFERENCE = "reference", "Reference"

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="attribute_definitions",
    )
    key = models.CharField(max_length=64)
    label = models.CharField(max_length=120)
    field_type = models.CharField(max_length=24, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    unique = models.BooleanField(default=False)
    restricted = models.BooleanField(default=False)

    class Meta:
        unique_together = [("category", "key")]

    def __str__(self) -> str:
        return f"{self.category.code}.{self.key}"


class AssetStatus(CoreModel):
    code = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=64)
    icon = models.CharField(max_length=64, blank=True, default="")
    semantic_treatment = models.CharField(max_length=32, default="neutral")
    is_terminal = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self) -> str:
        return self.label


class AssetCondition(CoreModel):
    code = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=64)
    icon = models.CharField(max_length=64, blank=True, default="")
    semantic_treatment = models.CharField(max_length=32, default="neutral")
    active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self) -> str:
        return self.label


class MaintenanceType(CoreModel):
    """Reference list of maintenance record types (FR-026)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class StatusTransitionRule(CoreModel):
    from_status = models.ForeignKey(
        AssetStatus,
        on_delete=models.PROTECT,
        related_name="transitions_from",
    )
    to_status = models.ForeignKey(
        AssetStatus,
        on_delete=models.PROTECT,
        related_name="transitions_to",
    )
    requires_reason = models.BooleanField(default=False)
    requires_evidence = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    allowed_roles = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = [("from_status", "to_status")]

    def __str__(self) -> str:
        return f"{self.from_status.code} -> {self.to_status.code}"
