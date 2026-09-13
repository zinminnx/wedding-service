from django.urls import path

from . import views

app_name = "checkins"

urlpatterns = [
    path("dashboard/check-in/", views.dashboard, name="dashboard"),
    path("reception/pass/<str:qr_token>/", views.scan, name="scan"),
    path("entry-qr/<str:qr_token>.svg", views.qr_image, name="qr_image"),
]
