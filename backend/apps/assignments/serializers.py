from rest_framework import serializers

from apps.accounts.models import User
from apps.assets.fields import UUIDRelatedField
from apps.assignments.models import Assignment, Reservation, TransferRecord
from apps.reference_data.models import AssetCondition, Department, Location


class AssignSerializer(serializers.Serializer):
    custodian = UUIDRelatedField(
        queryset=User.objects.filter(is_active=True),
        repr_fields=("username", "display_name"),
        required=False,
        allow_null=True,
    )
    department = UUIDRelatedField(
        queryset=Department.objects.filter(active=True),
        repr_fields=("code", "name"),
        required=False,
        allow_null=True,
    )
    location = UUIDRelatedField(
        queryset=Location.objects.filter(active=True),
        repr_fields=("code", "name"),
        required=False,
        allow_null=True,
    )
    expected_return_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReturnSerializer(serializers.Serializer):
    condition = UUIDRelatedField(
        queryset=AssetCondition.objects.filter(active=True),
        repr_fields=("code", "label"),
        required=False,
        allow_null=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    close_reason = serializers.CharField(required=False, allow_blank=True, default="returned")


class TransferSerializer(serializers.Serializer):
    to_custodian = UUIDRelatedField(
        queryset=User.objects.filter(is_active=True),
        repr_fields=("username", "display_name"),
        required=False,
        allow_null=True,
    )
    to_department = UUIDRelatedField(
        queryset=Department.objects.filter(active=True),
        repr_fields=("code", "name"),
        required=False,
        allow_null=True,
    )
    to_location = UUIDRelatedField(
        queryset=Location.objects.filter(active=True),
        repr_fields=("code", "name"),
        required=False,
        allow_null=True,
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    evidence = serializers.CharField(required=False, allow_blank=True, default="")
    confirm = serializers.BooleanField(required=False, default=False)


class ReserveSerializer(serializers.Serializer):
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CheckoutSerializer(serializers.Serializer):
    reservation = serializers.UUIDField()


class ExceptionReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(
        choices=["lost", "stolen", "missing", "damaged"], required=False
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    evidence = serializers.CharField(required=False, allow_blank=True, default="")
    resolve = serializers.BooleanField(required=False, default=False)
    resolution = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs.get("resolve") and not attrs.get("report_type"):
            raise serializers.ValidationError(
                {"report_type": ["Required unless resolving an open report."]}
            )
        return attrs


class RetireSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class DisposeSerializer(serializers.Serializer):
    method = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    force = serializers.BooleanField(required=False, default=False)


class ReopenSerializer(serializers.Serializer):
    justification = serializers.CharField(required=True, allow_blank=False)


def assignment_summary(assignment: Assignment) -> dict:
    return {
        "uuid": str(assignment.uuid),
        "asset": {"uuid": str(assignment.asset.uuid), "tag": assignment.asset.tag},
        "custodian": (
            {
                "uuid": str(assignment.custodian.uuid),
                "username": assignment.custodian.username,
                "display_name": assignment.custodian.display_name,
            }
            if assignment.custodian
            else None
        ),
        "department": (
            {"uuid": str(assignment.department.uuid), "name": assignment.department.name}
            if assignment.department
            else None
        ),
        "location": (
            {"uuid": str(assignment.location.uuid), "name": assignment.location.name}
            if assignment.location
            else None
        ),
        "assigned_at": assignment.assigned_at,
        "expected_return_at": assignment.expected_return_at,
        "acknowledged_at": assignment.acknowledged_at,
        "status": assignment.status,
    }


def transfer_summary(transfer: TransferRecord) -> dict:
    return {
        "uuid": str(transfer.uuid),
        "asset": {"uuid": str(transfer.asset.uuid), "tag": transfer.asset.tag},
        "status": transfer.status,
        "reason": transfer.reason,
        "confirmed_at": transfer.confirmed_at,
    }


def reservation_summary(reservation: Reservation) -> dict:
    return {
        "uuid": str(reservation.uuid),
        "asset": {"uuid": str(reservation.asset.uuid), "tag": reservation.asset.tag},
        "status": reservation.status,
        "start_at": reservation.start_at,
        "end_at": reservation.end_at,
        "purpose": reservation.purpose,
    }
