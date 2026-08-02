import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user with a single primary role (design section 9.3)."""

    class Role(models.TextChoices):
        SYSTEM_ADMIN = "system_admin", "System Administrator"
        ASSET_MANAGER = "asset_manager", "Asset Manager"
        DEPARTMENT_MANAGER = "department_manager", "Department Manager"
        OPERATOR = "operator", "Inventory Operator"
        EMPLOYEE = "employee", "Employee"
        AUDITOR = "auditor", "Auditor"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.EMPLOYEE)
    display_name = models.CharField(max_length=150, blank=True, default="")
    department = models.ForeignKey(
        "reference_data.Department",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="members",
    )
    locale = models.CharField(max_length=16, default="en")
    timezone = models.CharField(max_length=64, default="UTC")

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return self.display_name or self.get_full_name() or self.username


class UserScope(models.Model):
    """Organizational scope granted to a user (department / location / business unit)."""

    class ScopeType(models.TextChoices):
        DEPARTMENT = "department", "Department"
        LOCATION = "location", "Location"
        BUSINESS_UNIT = "business_unit", "Business unit"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scopes",
    )
    scope_type = models.CharField(max_length=16, choices=ScopeType.choices)
    department = models.ForeignKey(
        "reference_data.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    location = models.ForeignKey(
        "reference_data.Location",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    business_unit = models.CharField(max_length=64, blank=True, default="")

    def __str__(self) -> str:
        target = self.department or self.location or self.business_unit or ""
        return f"{self.user} @ {self.scope_type}:{target}"
