from rest_framework import serializers

from apps.accounts.models import User
from apps.reference_data.models import AssetCondition, Location
from apps.stocktakes.models import StocktakeObservation, StocktakeSession


class StocktakeSessionSerializer(serializers.ModelSerializer):
    locations = serializers.SlugRelatedField(
        slug_field="uuid",
        many=True,
        queryset=Location.objects.all(),
        required=False,
    )
    operators = serializers.SlugRelatedField(
        slug_field="uuid",
        many=True,
        queryset=User.objects.filter(is_active=True),
        required=False,
    )
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = StocktakeSession
        fields = [
            "uuid",
            "name",
            "locations",
            "operators",
            "start_at",
            "due_at",
            "snapshot_at",
            "status",
            "instructions",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "snapshot_at",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_created_by(self, obj) -> dict | None:
        if obj.created_by is None:
            return None
        return {"uuid": str(obj.created_by.uuid), "username": obj.created_by.username}


class StocktakeObservationSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField()
    location = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=Location.objects.all(),
        required=False,
        allow_null=True,
    )
    condition = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=AssetCondition.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = StocktakeObservation
        fields = [
            "uuid",
            "asset",
            "tag_scanned",
            "observed_at",
            "location",
            "condition",
            "note",
            "outcome",
        ]
        read_only_fields = ["uuid", "asset", "observed_at", "outcome"]

    def get_asset(self, obj) -> dict | None:
        if obj.asset is None:
            return None
        return {"uuid": str(obj.asset.uuid), "tag": obj.asset.tag, "name": obj.asset.name}
