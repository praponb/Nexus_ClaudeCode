from rest_framework import serializers

from apps.approvals.models import ApprovalRequest


class ApprovalSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField()
    requester = serializers.SerializerMethodField()
    approver = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = [
            "uuid",
            "request_type",
            "status",
            "asset",
            "requester",
            "approver",
            "to_code",
            "reason",
            "payload",
            "comments",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_asset(self, obj) -> dict:
        return {"uuid": str(obj.asset.uuid), "tag": obj.asset.tag, "name": obj.asset.name}

    def _user(self, user) -> dict | None:
        if user is None:
            return None
        return {
            "uuid": str(user.uuid),
            "username": user.username,
            "display_name": user.display_name,
        }

    def get_requester(self, obj) -> dict | None:
        return self._user(obj.requester)

    def get_approver(self, obj) -> dict | None:
        return self._user(obj.approver)


class ApprovalDecisionSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True, default="")
