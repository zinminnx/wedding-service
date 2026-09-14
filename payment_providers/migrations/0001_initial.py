from django.db import migrations, models
import django.db.models.deletion
import payment_providers.models


SEED_PROVIDERS = [
    ("kbz-bank", "KBZ Bank", "KBZ", "BANK", 10),
    ("aya-bank", "AYA Bank", "AYA", "BANK", 20),
    ("cb-bank", "CB Bank", "CB", "BANK", 30),
    ("uab-bank", "UAB Bank", "UAB", "BANK", 40),
    ("mab-bank", "MAB Bank", "MAB", "BANK", 50),
    ("kbzpay", "KBZPay", "KBZPay", "PAY", 110),
    ("wave-pay", "Wave Pay", "Wave", "PAY", 120),
    ("aya-pay", "AYA Pay", "AYA Pay", "PAY", 130),
]


def seed_and_backfill(apps, schema_editor):
    PaymentProvider = apps.get_model("payment_providers", "PaymentProvider")
    Link = apps.get_model("payment_providers", "PaymentMethodProviderLink")
    GiftPaymentMethod = apps.get_model("gifts", "GiftPaymentMethod")

    for key, name, short_name, provider_type, sort_order in SEED_PROVIDERS:
        PaymentProvider.objects.get_or_create(
            key=key,
            defaults={
                "name": name,
                "short_name": short_name,
                "provider_type": provider_type,
                "status": "ACTIVE",
                "sort_order": sort_order,
            },
        )

    from django.utils.text import slugify

    for method in GiftPaymentMethod.objects.all().iterator():
        provider = PaymentProvider.objects.filter(
            provider_type=method.method_type,
            name__iexact=method.name,
        ).first()

        if provider is None:
            base = slugify(method.name) or "provider"
            key = base
            counter = 2
            while PaymentProvider.objects.filter(key=key).exists():
                key = f"{base}-{method.method_type.lower()}-{counter}"
                counter += 1
            provider = PaymentProvider.objects.create(
                key=key,
                name=method.name,
                short_name=method.name[:60],
                provider_type=method.method_type,
                status="ACTIVE",
                sort_order=900,
            )

        Link.objects.update_or_create(
            payment_method_id=method.pk,
            defaults={"provider_id": provider.pk},
        )


def reverse_backfill(apps, schema_editor):
    # Keep provider master data on rollback; links disappear with the table.
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("gifts", "0004_remove_payment_method_name_unique"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentProvider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("short_name", models.CharField(blank=True, max_length=60)),
                ("provider_type", models.CharField(choices=[("BANK", "Bank"), ("PAY", "Mobile Pay")], db_index=True, max_length=12)),
                ("logo", models.FileField(blank=True, upload_to=payment_providers.models.provider_logo_upload_to)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("DISABLED", "Disabled")], db_index=True, default="ACTIVE", max_length=16)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["provider_type", "sort_order", "name", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="paymentprovider",
            constraint=models.UniqueConstraint(fields=("provider_type", "name"), name="unique_payment_provider_name_per_type"),
        ),
        migrations.CreateModel(
            name="PaymentMethodProviderLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("payment_method", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="provider_link", to="gifts.giftpaymentmethod")),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_accounts", to="payment_providers.paymentprovider")),
            ],
            options={"ordering": ["payment_method_id"]},
        ),
        migrations.RunPython(seed_and_backfill, reverse_backfill),
    ]
