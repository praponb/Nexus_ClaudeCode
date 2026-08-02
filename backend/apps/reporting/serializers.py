from rest_framework import serializers

from apps.reporting.models import SavedView

ALLOWED_CONFIG_KEYS = {"filters", "ordering", "columns", "page_size"}


class SavedViewSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()

    class Meta:
        model = SavedView
        fields = [
            "uuid",
            "name",
            "config",
            "shared",
            "is_default",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "owner", "created_at", "updated_at"]

    def get_owner(self, obj: SavedView) -> dict:
        return {"uuid": str(obj.owner.uuid), "username": obj.owner.username}

    def validate_config(self, value) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError("View configuration must be a JSON object.")
        unknown = set(value) - ALLOWED_CONFIG_KEYS
        if unknown:
            raise serializers.ValidationError(
                f"Unknown configuration keys: {', '.join(sorted(unknown))}."
            )
        filters = value.get("filters", {})
        if not isinstance(filters, dict):
            raise serializers.ValidationError("'filters' must be an object of filter values.")
        ordering = value.get("ordering")
        if ordering is not None and not isinstance(ordering, str):
            raise serializers.ValidationError("'ordering' must be a string.")
        columns = value.get("columns")
        if columns is not None and not (
            isinstance(columns, list) and all(isinstance(col, str) for col in columns)
        ):
            raise serializers.ValidationError("'columns' must be a list of strings.")
        page_size = value.get("page_size")
        if page_size is not None and not (isinstance(page_size, int) and 1 <= page_size <= 100):
            raise serializers.ValidationError("'page_size' must be an integer between 1 and 100.")
        return value
