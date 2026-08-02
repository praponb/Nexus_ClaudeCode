from rest_framework.routers import DefaultRouter

from apps.stocktakes.views import StocktakeViewSet

router = DefaultRouter()
router.register("stocktakes", StocktakeViewSet, basename="stocktake")

urlpatterns = router.urls
