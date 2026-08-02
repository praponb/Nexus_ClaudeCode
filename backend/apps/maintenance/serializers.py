from rest_framework import serializers

from apps.assets.fields import MoneyField, UUIDRelatedField
from apps.core import capabilities
from apps.maintenance.models import MaintenanceRecord
from apps.reference_data.models import MaintenanceType


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    """Maintenance record representation (FR-011).

    ``cost`` uses the shared MoneyField with ``source="*"``, so validated data
    already carries flat ``cost`` / ``cost_currency`` values for the service
    layer. The field is removed entirely for roles without ``finance.view``.
    """

    asset = serializers.SerializerMethodField()
    maintenance_type = UUIDRelatedField(
        queryset=MaintenanceType.objects.filter(active=True),
        repr_fields=("code", "name"),
    )
    cost = MoneyField(amount_attr="cost", currency_attr="cost_currency", required=False)

    class Meta:
        model = MaintenanceRecord
        fields = [
            "uuid",
            "asset",
            "maintenance_type",
            "issue",
            "provider",
            "technician",
            "started_at",
            "completed_at",
            "cost",
            "result",
            "next_due",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "asset",
            "started_at",
            "completed_at",
            "status",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated and capabilities.can_view_finance(user)):
            # Field-level finance restriction on maintenance cost (FR-011).
            self.fields.pop("cost", None)

    def get_asset(self, obj) -> dict:
        return {"uuid": str(obj.asset.uuid), "tag": obj.asset.tag, "name": obj.asset.name}


class MaintenanceCompleteSerializer(serializers.Serializer):
    result = serializers.CharField(required=False, allow_blank=True, default="")
    next_due = serializers.DateField(required=False, allow_null=True)
    cost = MoneyField(amount_attr="cost", currency_attr="cost_currency", required=False)
