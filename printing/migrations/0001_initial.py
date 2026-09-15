import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import printing.models


def activate_printing(apps, schema_editor):
    FeatureModule = apps.get_model("modules", "FeatureModule")
    ServicePackage = apps.get_model("modules", "ServicePackage")
    Wedding = apps.get_model("weddings", "Wedding")
    WeddingPrintSettings = apps.get_model("printing", "WeddingPrintSettings")

    module, _ = FeatureModule.objects.update_or_create(
        key="printing",
        defaults={
            "name": "Printing",
            "description": "Cloud print queue for approved wedding photos; local printer agent arrives in v12.3.",
            "version": "1.0",
            "module_type": "OPTIONAL",
            "system_enabled": True,
            "visible_to_weddings": True,
            "sort_order": 200,
            "allowed_roles": ["WEDDING_OWNER", "WEDDING_MANAGER", "PRINT_STAFF"],
        },
    )
    photos = FeatureModule.objects.filter(key="photos").first()
    if photos:
        module.dependencies.set([photos])
    package = ServicePackage.objects.filter(is_active=True, is_default=True).first()
    if package:
        package.modules.add(module)
    for wedding in Wedding.objects.all().only("pk"):
        WeddingPrintSettings.objects.get_or_create(wedding_id=wedding.pk)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("modules", "0001_initial"),
        ("photos", "0002_storage_object"),
        ("weddings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WeddingPrintSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("queue_enabled", models.BooleanField(default=True)),
                ("queue_paused", models.BooleanField(default=False)),
                ("default_copies", models.PositiveSmallIntegerField(default=1)),
                ("default_paper_size", models.CharField(default="4X6", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="print_settings", to="weddings.wedding")),
            ],
            options={"verbose_name": "Wedding print settings", "verbose_name_plural": "Wedding print settings"},
        ),
        migrations.CreateModel(
            name="PrintJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.CharField(default=printing.models.generate_print_public_id, editable=False, max_length=20, unique=True)),
                ("status", models.CharField(choices=[("QUEUED", "Queued"), ("CLAIMED", "Claimed"), ("PRINTING", "Printing"), ("PRINTED", "Printed"), ("FAILED", "Failed"), ("CANCELLED", "Cancelled")], db_index=True, default="QUEUED", max_length=16)),
                ("copies", models.PositiveSmallIntegerField(default=1)),
                ("paper_size", models.CharField(choices=[("4X6", "4 × 6 in"), ("5X7", "5 × 7 in"), ("A6", "A6"), ("A5", "A5"), ("A4", "A4"), ("CUSTOM", "Custom / Printer default")], default="4X6", max_length=16)),
                ("fit_mode", models.CharField(choices=[("FIT", "Fit entire image"), ("FILL", "Fill page / crop"), ("ORIGINAL", "Original size")], default="FIT", max_length=16)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("source_token", models.CharField(default=printing.models.generate_source_token, editable=False, max_length=64, unique=True)),
                ("claimed_by_label", models.CharField(blank=True, max_length=120)),
                ("error_message", models.CharField(blank=True, max_length=500)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("printing_started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("photo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="print_jobs", to="photos.weddingphoto")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="requested_print_jobs", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="print_jobs", to="weddings.wedding")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["wedding", "status", "created_at"], name="print_wed_status_idx"),
                    models.Index(fields=["wedding", "created_at"], name="print_wed_time_idx"),
                ],
            },
        ),
        migrations.RunPython(activate_printing, noop_reverse),
    ]
