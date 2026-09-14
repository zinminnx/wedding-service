from django.urls import path

from . import views

app_name = "gifts"

urlpatterns = [
    path("", views.gift_dashboard, name="dashboard"),
    path("inventory/", views.return_gift_inventory, name="inventory"),
    path("reports/", views.payment_report, name="report"),
    path("reports/export.csv", views.payment_report_csv, name="report_csv"),
    path("payment-method/<int:method_id>/action/", views.payment_method_action, name="payment_method_action"),
    path("declaration/<int:declaration_id>/action/", views.declaration_action, name="declaration_action"),
]
