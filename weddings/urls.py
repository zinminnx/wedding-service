from django.urls import path

from . import views

app_name = "weddings"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("wedding/", views.wedding_overview, name="overview"),
]
