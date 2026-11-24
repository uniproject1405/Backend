from django.urls import path
from . import views

urlpatterns = [
    path("", views.users_api, name="users-api"),
    path("register/", views.RegisterView.as_view(), name="user-register"),
    path("login/", views.LoginView.as_view(), name="user-login"),
    path("me/", views.CurrentUserView.as_view(), name="user-current"),
    path("me/profile/", views.ProfileCreateView.as_view(), name="profile-create"),
    path("logout/", views.LogoutView.as_view(), name="user-logout"),
]
