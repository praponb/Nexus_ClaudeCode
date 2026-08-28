from django.urls import path

from apps.accounts.views import (
    CsrfTokenView,
    LoginView,
    LogoutView,
    MeView,
    MfaConfirmView,
    MfaSetupView,
    MfaVerifyView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("2fa/setup/", MfaSetupView.as_view(), name="auth-mfa-setup"),
    path("2fa/confirm/", MfaConfirmView.as_view(), name="auth-mfa-confirm"),
    path("2fa/verify/", MfaVerifyView.as_view(), name="auth-mfa-verify"),
]
