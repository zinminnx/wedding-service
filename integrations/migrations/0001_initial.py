from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_storage_settings(apps, schema_editor):
    Wedding = apps.get_model("weddings", "Wedding")
    WeddingStorageSettings = apps.get_model("integrations", "WeddingStorageSettings")
    for wedding_id in Wedding.objects.values_list("id", flat=True).iterator():
        WeddingStorageSettings.objects.get_or_create(wedding_id=wedding_id)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weddings", "0003_venue_master_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeddingStorageSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("LOCAL", "Local Media"), ("ONEDRIVE", "Microsoft OneDrive")], db_index=True, default="LOCAL", max_length=16)),
                ("onedrive_drive_id", models.CharField(blank=True, max_length=180)),
                ("root_folder", models.CharField(blank=True, max_length=220)),
                ("health_status", models.CharField(choices=[("UNKNOWN", "Unknown"), ("OK", "Healthy"), ("ERROR", "Error")], db_index=True, default="UNKNOWN", max_length=16)),
                ("health_message", models.CharField(blank=True, max_length=255)),
                ("last_health_check_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="storage_settings", to="weddings.wedding")),
            ],
            options={"verbose_name": "Wedding storage settings", "verbose_name_plural": "Wedding storage settings"},
        ),
        migrations.CreateModel(
            name="StoredObject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("backend", models.CharField(choices=[("LOCAL", "Local Media"), ("ONEDRIVE", "Microsoft OneDrive")], db_index=True, max_length=16)),
                ("category", models.CharField(choices=[("PHOTO", "Photo"), ("FINANCIAL_DOCUMENT", "Financial Document"), ("ARCHIVE", "Archive"), ("OTHER", "Other")], db_index=True, default="OTHER", max_length=32)),
                ("relative_path", models.CharField(max_length=500)),
                ("remote_item_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("remote_web_url", models.URLField(blank=True, max_length=1000)),
                ("mime_type", models.CharField(blank=True, max_length=160)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("sha256", models.CharField(blank=True, db_index=True, max_length=64)),
                ("source_app", models.CharField(blank=True, max_length=80)),
                ("source_model", models.CharField(blank=True, max_length=80)),
                ("source_object_id", models.CharField(blank=True, max_length=80)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("AVAILABLE", "Available"), ("FAILED", "Failed"), ("DELETED", "Deleted")], db_index=True, default="PENDING", max_length=16)),
                ("last_error", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_storage_objects", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stored_objects", to="weddings.wedding")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["wedding", "backend", "status"], name="storage_wed_backend_idx"),
                    models.Index(fields=["wedding", "category"], name="storage_wed_cat_idx"),
                    models.Index(fields=["source_app", "source_model", "source_object_id"], name="storage_source_idx"),
                ],
            },
        ),
        migrations.RunPython(create_storage_settings, migrations.RunPython.noop),
    ]
