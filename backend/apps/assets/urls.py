from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.assets.views import AssetSearchView, AssetViewSet

router = DefaultRouter()
router.register("assets", AssetViewSet, basename="asset")

urlpatterns = [
    path("search/assets/", AssetSearchView.as_view(), name="asset-search"),
    path("", include(router.urls)),
]
