from django.urls import path

from . import views

app_name = "staffing"

urlpatterns = [
    path("", views.staff_list, name="list"),
    path("add/", views.staff_add, name="add"),
    path("<int:membership_id>/edit/", views.staff_edit, name="edit"),
    path("<int:membership_id>/disable/", views.staff_disable, name="disable"),
]
