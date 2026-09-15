import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import audit_analytics.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weddings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.CharField(default=audit_analytics.models.generate_audit_public_id, editable=False, max_length=24, unique=True)),
                ("actor_label", models.CharField(blank=True, max_length=160)),
                ("actor_role", models.CharField(blank=True, max_length=40)),
                ("category", models.CharField(choices=[("SYSTEM", "System"), ("WEDDING", "Wedding"), ("ACCESS", "Access & Staff"), ("GUESTS", "Guests"), ("INVITATIONS", "Invitations"), ("RSVP", "RSVP"), ("GIFTS", "Gifts & Payments"), ("CHECKIN", "Check-in"), ("PHOTOS", "Photos"), ("PRINTING", "Printing"), ("PLANNER", "Planner & Vendors"), ("FINANCE", "Finance"), ("STORAGE", "Storage"), ("ARCHIVE", "Archive & Restore"), ("THEME", "Themes"), ("MODULE", "Modules")], db_index=True, default="SYSTEM", max_length=20)),
                ("action", models.CharField(db_index=True, max_length=128)),
                ("entity_type", models.CharField(blank=True, max_length=80)),
                ("entity_id", models.CharField(blank=True, max_length=80)),
                ("message", models.CharField(blank=True, max_length=500)),
                ("route_name", models.CharField(blank=True, max_length=160)),
                ("status_code", models.PositiveSmallIntegerField(default=0)),
                ("source", models.CharField(choices=[("MIDDLEWARE", "Request audit"), ("BACKFILL", "Historical backfill"), ("MANUAL", "Application event")], db_index=True, default="MANUAL", max_length=16)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("source_fingerprint", models.CharField(blank=True, editable=False, max_length=64, null=True, unique=True)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="everafter_audit_events", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="weddings.wedding")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["wedding", "created_at"], name="audit_wed_time_idx"),
                    models.Index(fields=["wedding", "category"], name="audit_wed_cat_idx"),
                    models.Index(fields=["wedding", "actor"], name="audit_wed_actor_idx"),
                ],
            },
        ),
    ]
