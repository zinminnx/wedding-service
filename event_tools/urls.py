from django.urls import path

from . import views

app_name = "event_tools"

urlpatterns = [
    path("dashboard/event-tools/", views.settings_view, name="settings"),
    path("i/<str:token>/calendar.ics", views.calendar_ics, name="calendar_ics"),
]
