from django.urls import path

from . import views

app_name = "archive_restore"

urlpatterns = [
    path("dashboard/archive/", views.dashboard, name="dashboard"),
    path("dashboard/archive/create/", views.create_snapshot, name="create"),
    path("dashboard/archive/<str:public_id>/verify/", views.verify_snapshot_view, name="verify"),
    path("dashboard/archive/<str:public_id>/download/", views.download_snapshot, name="download"),
    path("dashboard/archive/<str:public_id>/archive/", views.archive_wedding, name="archive_wedding"),
    path("dashboard/archive/<str:public_id>/restore/", views.restore_wedding, name="restore_wedding"),
    path("dashboard/archive/<str:public_id>/delete-pending/", views.mark_delete_pending, name="delete_pending"),
]
