from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.approvals.views import ApprovalViewSet

router = DefaultRouter()
router.register("approvals", ApprovalViewSet, basename="approval")

urlpatterns = [
    path("", include(router.urls)),
]
