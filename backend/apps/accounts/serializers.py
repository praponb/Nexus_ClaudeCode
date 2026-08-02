from rest_framework import serializers

from apps.accounts.models import User, UserScope
from apps.core import capabilities


class UserScopeSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = UserScope
        fields = ["scope_type", "department", "location", "business_unit"]

    def get_department(self, obj: UserScope) -> dict | None:
        if obj.department is None:
            return None
        return {"uuid": str(obj.department.uuid), "name": obj.department.name}

    def get_location(self, obj: UserScope) -> dict | None:
        if obj.location is None:
            return None
        return {"uuid": str(obj.location.uuid), "name": obj.location.name}


class MeSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    scopes = UserScopeSerializer(many=True, read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "uuid",
            "username",
            "email",
            "display_name",
            "role",
            "department",
            "locale",
            "timezone",
            "scopes",
            "capabilities",
            "is_active",
        ]

    def get_department(self, obj: User) -> dict | None:
        if obj.department is None:
            return None
        return {"uuid": str(obj.department.uuid), "name": obj.department.name}

    def get_capabilities(self, obj: User) -> list[str]:
        return capabilities.capabilities_for(obj)
