from django.urls import path

from . import views

app_name = "rsvp"

urlpatterns = [
    path("", views.rsvp_list, name="list"),
]
