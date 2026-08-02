from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import NotificationPreferencesView, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path(
        "notifications/preferences/",
        NotificationPreferencesView.as_view(),
        name="notification-preferences",
    ),
    path("", include(router.urls)),
]
