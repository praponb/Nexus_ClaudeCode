import django_filters

from apps.assets.models import Asset
from apps.assignments.models import Assignment


class AssetFilter(django_filters.FilterSet):
    category = django_filters.UUIDFilter(field_name="category__uuid")
    status = django_filters.UUIDFilter(field_name="status__uuid")
    status_code = django_filters.CharFilter(field_name="status__code")
    condition = django_filters.UUIDFilter(field_name="condition__uuid")
    department = django_filters.UUIDFilter(field_name="department__uuid")
    location = django_filters.UUIDFilter(field_name="location__uuid")
    custodian = django_filters.UUIDFilter(field_name="custodian__uuid")
    supplier = django_filters.UUIDFilter(field_name="supplier__uuid")
    record_status = django_filters.CharFilter(field_name="record_status")
    warranty_end_before = django_filters.DateFilter(field_name="warranty_end", lookup_expr="lte")
    warranty_end_after = django_filters.DateFilter(field_name="warranty_end", lookup_expr="gte")
    maintenance_due_before = django_filters.DateFilter(
        field_name="next_maintenance_due", lookup_expr="lte"
    )
    assigned = django_filters.BooleanFilter(method="filter_assigned")

    class Meta:
        model = Asset
        fields: list[str] = []

    def filter_assigned(self, queryset, name, value):
        # Match only assets that HAVE an open assignment row; a LEFT JOIN on
        # returned_at__isnull would also match assets with no assignments.
        active_asset_ids = Assignment.objects.filter(returned_at__isnull=True).values("asset_id")
        if value:
            return queryset.filter(id__in=active_asset_ids)
        return queryset.exclude(id__in=active_asset_ids)
