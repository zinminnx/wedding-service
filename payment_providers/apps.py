from django.apps import AppConfig


class PaymentProvidersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payment_providers"
    verbose_name = "Payment Providers"
