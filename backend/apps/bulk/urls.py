from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.bulk.views import ExportJobViewSet, ImportJobViewSet, ImportTemplateView

router = DefaultRouter()
router.register("imports", ImportJobViewSet, basename="import-job")
router.register("exports", ExportJobViewSet, basename="export-job")

urlpatterns = [
    path("imports/template/", ImportTemplateView.as_view(), name="import-template"),
    *router.urls,
]
