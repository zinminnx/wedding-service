from django.urls import path

from . import views

app_name = "gifts"

urlpatterns = [
    path("", views.gift_dashboard, name="dashboard"),
    path("inventory/", views.return_gift_inventory, name="inventory"),
    path("payment-method/<int:method_id>/action/", views.payment_method_action, name="payment_method_action"),
    path("declaration/<int:declaration_id>/action/", views.declaration_action, name="declaration_action"),
]
