from django.urls import path

from . import views

app_name = "vendors"

urlpatterns = [
    path("dashboard/vendors/", views.dashboard, name="dashboard"),
    path("dashboard/vendors/new/", views.vendor_form, name="vendor_create"),
    path("dashboard/vendors/<int:pk>/edit/", views.vendor_form, name="vendor_edit"),
    path("dashboard/vendors/quotes/new/", views.quote_form, name="quote_create"),
    path("dashboard/vendors/quotes/<int:pk>/edit/", views.quote_form, name="quote_edit"),
    path("dashboard/vendors/quotes/<int:pk>/action/", views.quote_action, name="quote_action"),
]
