from rest_framework.routers import DefaultRouter

from apps.maintenance.views import MaintenanceViewSet

router = DefaultRouter()
router.register("maintenance", MaintenanceViewSet, basename="maintenance")

urlpatterns = router.urls
