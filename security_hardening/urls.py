from django.urls import path

from . import views

app_name = "security_hardening"

urlpatterns = [
    path("live/", views.live, name="live"),
    path("ready/", views.ready, name="ready"),
]
