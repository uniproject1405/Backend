from django.urls import path
from . import views

urlpatterns = [
    path("", views.users_api, name="users-api"),
    path("register/", views.RegisterView.as_view(), name="user-register"),
    path("login/", views.LoginView.as_view(), name="user-login"),
    path("me/", views.CurrentUserView.as_view(), name="user-current"),
    path("me/profile/", views.ProfileCreateView.as_view(), name="profile-create"),
    path("logout/", views.LogoutView.as_view(), name="user-logout"),
    # Google authentication endpoints
    path("google/", views.GoogleAuthView.as_view(), name="google-auth"),
    path("google/login/", views.GoogleLoginRedirectView.as_view(), name="google-login-redirect"),
    path("google/callback/", views.GoogleCallbackView.as_view(), name="google-callback"),

    # Password reset & change endpoints
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/validate/", views.PasswordResetValidateView.as_view(), name="password-reset-validate"),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("password-change/", views.PasswordChangeView.as_view(), name="password-change"),

    # Partner explore & discovery endpoints
    path("explore/", views.PartnerExploreView.as_view(), name="user-explore"),
    path("discover/", views.PartnerExploreView.as_view(), name="user-discover"),

    # Self profile management endpoints
    path("profile/", views.MyProfileView.as_view(), name="user-profile-manage"),
    path("profile/completion/", views.ProfileCompletionView.as_view(), name="user-profile-completion"),

    # Public user & profile endpoints
    path("<uuid:public_id>/", views.UserDetailView.as_view(), name="user-detail"),
    path("<uuid:public_id>/profile/", views.PublicProfileDetailView.as_view(), name="user-public-profile"),
]
