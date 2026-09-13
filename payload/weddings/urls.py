from django.urls import path

from . import views

app_name = "weddings"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("wedding/", views.wedding_overview, name="overview"),
    path("weddings/", views.wedding_list, name="list"),
    path("weddings/new/", views.wedding_create, name="create"),
    path("weddings/<str:public_id>/switch/", views.switch_wedding, name="switch"),
]
