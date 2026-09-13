from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def bootstrap_inventory(apps, schema_editor):
    GiftSettings = apps.get_model("gifts", "GiftSettings")
    ReturnGiftInventory = apps.get_model("gifts", "ReturnGiftInventory")
    ReturnGiftMovement = apps.get_model("gifts", "ReturnGiftMovement")
    CheckIn = apps.get_model("checkins", "CheckIn")

    for gift_settings in GiftSettings.objects.all().iterator():
        issued_rows = list(
            CheckIn.objects.filter(
                wedding_id=gift_settings.wedding_id,
                return_gift_quantity__gt=0,
            ).order_by("return_gift_issued_at", "id")
        )
        issued_total = sum(row.return_gift_quantity for row in issued_rows)
        opening_total = max(gift_settings.return_gift_stock, issued_total)

        inventory, _ = ReturnGiftInventory.objects.get_or_create(
            wedding_id=gift_settings.wedding_id,
            defaults={
                "quantity_on_hand": opening_total,
                "low_stock_threshold": 10,
            },
        )

        balance = opening_total
        if opening_total > 0:
            ReturnGiftMovement.objects.create(
                wedding_id=gift_settings.wedding_id,
                inventory_id=inventory.id,
                movement_type="OPENING",
                quantity_delta=opening_total,
                quantity_after=opening_total,
                note="Opening balance migrated from the pre-v9 return gift stock.",
            )

        for row in issued_rows:
            balance = max(balance - row.return_gift_quantity, 0)
            ReturnGiftMovement.objects.create(
                wedding_id=gift_settings.wedding_id,
                inventory_id=inventory.id,
                guest_id=row.guest_id,
                checkin_id=row.id,
                movement_type="ISSUE",
                quantity_delta=-row.return_gift_quantity,
                quantity_after=balance,
                note="Existing return gift issue migrated during v9 upgrade.",
                created_by_id=row.return_gift_issued_by_id,
            )

        inventory.quantity_on_hand = balance
        inventory.save(update_fields=["quantity_on_hand"])
        if gift_settings.return_gift_stock != opening_total:
            gift_settings.return_gift_stock = opening_total
            gift_settings.save(update_fields=["return_gift_stock"])


def reverse_bootstrap(apps, schema_editor):
    ReturnGiftMovement = apps.get_model("gifts", "ReturnGiftMovement")
    ReturnGiftInventory = apps.get_model("gifts", "ReturnGiftInventory")
    ReturnGiftMovement.objects.all().delete()
    ReturnGiftInventory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("checkins", "0001_initial"),
        ("gifts", "0002_alter_guestgiftdeclaration_payment_method_and_more"),
        ("guests", "0001_initial"),
        ("weddings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="giftsettings",
            name="return_gift_allow_staff_override",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="giftsettings",
            name="return_gift_requires_checkin",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="ReturnGiftInventory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity_on_hand", models.PositiveIntegerField(default=0)),
                ("low_stock_threshold", models.PositiveIntegerField(default=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "wedding",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="return_gift_inventory",
                        to="weddings.wedding",
                    ),
                ),
            ],
            options={"verbose_name_plural": "Return gift inventories"},
        ),
        migrations.CreateModel(
            name="ReturnGiftMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "movement_type",
                    models.CharField(
                        choices=[
                            ("OPENING", "Opening balance"),
                            ("RESTOCK", "Stock added"),
                            ("SET_STOCK", "Stock corrected"),
                            ("ISSUE", "Issued to guest"),
                            ("RETURN", "Returned to stock"),
                        ],
                        max_length=16,
                    ),
                ),
                ("quantity_delta", models.IntegerField()),
                ("quantity_after", models.PositiveIntegerField()),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "checkin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="return_gift_movements",
                        to="checkins.checkin",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="return_gift_inventory_actions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "guest",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="return_gift_movements",
                        to="guests.guest",
                    ),
                ),
                (
                    "inventory",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movements",
                        to="gifts.returngiftinventory",
                    ),
                ),
                (
                    "wedding",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="return_gift_movements",
                        to="weddings.wedding",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="returngiftmovement",
            index=models.Index(fields=["wedding", "created_at"], name="returngift_wed_time_idx"),
        ),
        migrations.RunPython(bootstrap_inventory, reverse_bootstrap),
    ]
