from django.urls import path

from . import views

app_name = "integrations"

urlpatterns = [
    path("dashboard/storage/", views.storage_dashboard, name="storage_dashboard"),
]
