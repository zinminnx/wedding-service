from django.urls import path

from . import views

app_name = "audit_analytics"

urlpatterns = [
    path("dashboard/analytics/", views.analytics_dashboard, name="dashboard"),
    path("dashboard/analytics/export/", views.analytics_export, name="analytics_export"),
    path("dashboard/audit/", views.audit_trail, name="audit"),
    path("dashboard/audit/export/", views.audit_export, name="audit_export"),
]
