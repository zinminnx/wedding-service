import archive_restore.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("integrations", "0001_initial"),
        ("weddings", "0003_venue_master_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchiveSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.CharField(default=archive_restore.models.generate_archive_public_id, editable=False, max_length=24, unique=True)),
                ("wedding_public_id", models.CharField(db_index=True, max_length=30)),
                ("wedding_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("BUILDING", "Building"), ("READY", "Ready"), ("VERIFY_FAILED", "Verification Failed"), ("FAILED", "Failed"), ("RESTORING", "Restoring"), ("RESTORED", "Restored")], db_index=True, default="BUILDING", max_length=24)),
                ("archive_size", models.PositiveBigIntegerField(default=0)),
                ("sha256", models.CharField(blank=True, db_index=True, max_length=64)),
                ("data_object_count", models.PositiveIntegerField(default=0)),
                ("file_count", models.PositiveIntegerField(default=0)),
                ("manifest", models.JSONField(blank=True, default=dict)),
                ("last_error", models.CharField(blank=True, max_length=1000)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("restored_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_archive_snapshots", to=settings.AUTH_USER_MODEL)),
                ("stored_object", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="archive_snapshot", to="integrations.storedobject")),
                ("wedding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="archive_snapshots", to="weddings.wedding")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="ArchiveEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("wedding_public_id", models.CharField(db_index=True, max_length=30)),
                ("action", models.CharField(choices=[("EXPORT_STARTED", "Export Started"), ("EXPORT_READY", "Export Ready"), ("EXPORT_FAILED", "Export Failed"), ("VERIFIED", "Verified"), ("VERIFY_FAILED", "Verify Failed"), ("ARCHIVED", "Wedding Archived"), ("RESTORED", "Wedding Restored"), ("DELETE_PENDING", "Delete Pending"), ("DOWNLOADED", "Archive Downloaded")], db_index=True, max_length=32)),
                ("message", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="archive_events", to=settings.AUTH_USER_MODEL)),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="archive_restore.archivesnapshot")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(model_name="archivesnapshot", index=models.Index(fields=["wedding_public_id", "status"], name="archive_wed_status_idx")),
        migrations.AddIndex(model_name="archivesnapshot", index=models.Index(fields=["wedding", "created_at"], name="archive_wed_time_idx")),
        migrations.AddIndex(model_name="archiveevent", index=models.Index(fields=["wedding_public_id", "created_at"], name="archive_evt_wed_time_idx")),
    ]
