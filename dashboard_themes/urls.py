from django.urls import path

from . import views

app_name = "dashboard_themes"

urlpatterns = [
    path("dashboard/themes/", views.gallery, name="gallery"),
    path("dashboard/themes/manage/", views.manage, name="manage"),
    path("dashboard/themes/manage/new/", views.theme_create, name="create"),
    path("dashboard/themes/manage/<int:pk>/edit/", views.theme_edit, name="edit"),
    path("dashboard/themes/manage/<int:pk>/action/", views.theme_action, name="action"),
]
