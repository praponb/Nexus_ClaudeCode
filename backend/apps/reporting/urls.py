from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.reporting.report_views import ReportCatalogView, ReportDetailView, ReportExportView
from apps.reporting.views import DashboardSummaryView, DataQualityIssuesView, SavedViewViewSet

router = DefaultRouter()
router.register("saved-views", SavedViewViewSet, basename="saved-view")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("data-quality/issues/", DataQualityIssuesView.as_view(), name="data-quality-issues"),
    path("reports/", ReportCatalogView.as_view(), name="report-catalog"),
    path("reports/<str:report_type>/", ReportDetailView.as_view(), name="report-detail"),
    path(
        "reports/<str:report_type>/export/",
        ReportExportView.as_view(),
        name="report-export",
    ),
    path("", include(router.urls)),
]
