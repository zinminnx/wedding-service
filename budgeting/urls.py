from django.urls import path

from . import views

app_name = "budgeting"

urlpatterns = [
    path("dashboard/budget/", views.dashboard, name="dashboard"),
    path("dashboard/budget/items/new/", views.item_create, name="item_create"),
    path("dashboard/budget/items/<int:item_id>/edit/", views.item_edit, name="item_edit"),
    path("dashboard/budget/items/<int:item_id>/delete/", views.item_delete, name="item_delete"),
]
