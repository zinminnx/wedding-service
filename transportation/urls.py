from django.urls import path

from . import views

app_name = "transportation"

urlpatterns = [
    path("dashboard/transportation/", views.settings_view, name="settings"),
    path("transportation/guide/<str:token>/", views.guest_guide, name="guest_guide"),
]
