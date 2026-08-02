from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.permissions import AllowAny

from apps.core.health import LivenessView, ReadinessView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/health/live/", LivenessView.as_view(), name="health-live"),
    path("api/v1/health/ready/", ReadinessView.as_view(), name="health-ready"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/admin/", include("apps.accounts.admin_urls")),
    path("api/v1/reference-data/", include("apps.reference_data.urls")),
    path("api/v1/", include("apps.assignments.urls")),
    path("api/v1/", include("apps.maintenance.urls")),
    path("api/v1/", include("apps.stocktakes.urls")),
    path("api/v1/", include("apps.bulk.urls")),
    path("api/v1/", include("apps.approvals.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.assets.urls")),
    path("api/v1/", include("apps.reporting.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="openapi-schema",
    ),
]
