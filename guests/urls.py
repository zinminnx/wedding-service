from django.urls import path

from . import views

app_name = "guests"

urlpatterns = [
    path("", views.guest_list, name="list"),
    path("add/", views.guest_create, name="add"),
    path("<str:public_id>/edit/", views.guest_edit, name="edit"),
]
