from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.assignments.views import AssignmentViewSet, ReservationViewSet

router = DefaultRouter()
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = [
    path("", include(router.urls)),
]
