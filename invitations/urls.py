from django.urls import path

from . import views

app_name = "invitations"

urlpatterns = [
    path("i/<str:token>/", views.invitation_detail, name="detail"),
    path("dashboard/invitations/", views.invitation_list, name="list"),
    path(
        "dashboard/invitations/generate-missing/",
        views.generate_missing_invitations,
        name="generate_missing",
    ),
    path(
        "dashboard/invitations/generate/<str:guest_public_id>/",
        views.generate_guest_invitation,
        name="generate_guest",
    ),
    path(
        "dashboard/invitations/<int:invitation_id>/action/",
        views.invitation_action,
        name="action",
    ),
]
