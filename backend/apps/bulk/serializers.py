from rest_framework import serializers

from apps.bulk.models import ExportJob, ImportJob


class ImportJobSerializer(serializers.ModelSerializer):
    requester = serializers.SerializerMethodField()

    class Meta:
        model = ImportJob
        fields = [
            "uuid",
            "requester",
            "original_filename",
            "policy",
            "status",
            "total_rows",
            "created_count",
            "updated_count",
            "skipped_count",
            "failed_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_requester(self, obj) -> dict:
        return {"uuid": str(obj.requester.uuid), "username": obj.requester.username}


class ExportJobSerializer(serializers.ModelSerializer):
    requester = serializers.SerializerMethodField()

    class Meta:
        model = ExportJob
        fields = [
            "uuid",
            "requester",
            "filters",
            "status",
            "row_count",
            "error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_requester(self, obj) -> dict:
        return {"uuid": str(obj.requester.uuid), "username": obj.requester.username}
