from django.urls import path

from . import views

app_name = "photos"

urlpatterns = [
    path("dashboard/photos/", views.dashboard, name="dashboard"),
    path("dashboard/photos/settings/", views.update_settings, name="settings"),
    path("dashboard/photos/upload/", views.staff_upload, name="staff_upload"),
    path("dashboard/photos/bulk/", views.bulk_action, name="bulk_action"),
    path("dashboard/photos/<str:public_id>/action/", views.photo_action, name="photo_action"),
    path("dashboard/photos/<str:public_id>/file/", views.staff_file, name="staff_file"),
    path("dashboard/photos/<str:public_id>/download/", views.staff_download, name="staff_download"),
    path("i/<str:token>/photos/", views.guest_gallery, name="guest_upload"),
    path("i/<str:token>/photos/<str:public_id>/file/", views.guest_file, name="guest_file"),
    path("i/<str:token>/photos/<str:public_id>/download/", views.guest_download, name="guest_download"),
    path("photos/live/<str:token>/", views.slideshow, name="slideshow"),
    path("photos/live/<str:token>/feed/", views.slideshow_feed, name="slideshow_feed"),
    path("photos/live/<str:token>/file/<str:public_id>/", views.slideshow_file, name="slideshow_file"),
]
