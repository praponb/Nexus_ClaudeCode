from rest_framework.routers import DefaultRouter

from apps.reference_data.views import (
    AssetConditionViewSet,
    AssetStatusViewSet,
    CategoryViewSet,
    CostCenterViewSet,
    DepartmentViewSet,
    LocationViewSet,
    MaintenanceTypeViewSet,
    StatusTransitionRuleViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="ref-category")
router.register("statuses", AssetStatusViewSet, basename="ref-status")
router.register("conditions", AssetConditionViewSet, basename="ref-condition")
router.register("departments", DepartmentViewSet, basename="ref-department")
router.register("locations", LocationViewSet, basename="ref-location")
router.register("cost-centers", CostCenterViewSet, basename="ref-cost-center")
router.register("suppliers", SupplierViewSet, basename="ref-supplier")
router.register("maintenance-types", MaintenanceTypeViewSet, basename="ref-maintenance-type")
router.register("transition-rules", StatusTransitionRuleViewSet, basename="ref-transition-rule")

urlpatterns = router.urls
