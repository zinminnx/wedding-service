from django.contrib.auth import views as auth_views
from django.urls import path

from . import profile_views
from . import profile_media_views
from . import role_views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html", redirect_authenticated_user=True),
        name="login",
    ),
    path("profile/", profile_views.profile, name="profile"),
    path("profile/photo/upload/", profile_media_views.profile_photo_upload, name="profile_photo_upload"),
    path("profile/photo/remove/", profile_media_views.profile_photo_remove, name="profile_photo_remove"),
    path("profile/photo/thumb/", profile_media_views.profile_thumbnail, name="profile_thumb"),
    path("media/wedding/<str:wedding_public_id>/thumb/", profile_media_views.wedding_cover_thumbnail, name="wedding_cover_thumb"),
    path("roles/", role_views.role_management, name="roles"),
    path("roles/global/<int:user_id>/", role_views.global_role_update, name="global_role_update"),
    path("roles/wedding/<int:membership_id>/", role_views.wedding_role_update, name="wedding_role_update"),
    path("profile/edit/", profile_views.profile_edit, name="profile_edit"),
    path("password/change/", profile_views.password_change, name="password_change"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="accounts:login"),
        name="logout",
    ),
]
