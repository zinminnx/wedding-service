# Generated for EverVow v10 guest photo workflow.

import django.db.models.deletion
import photos.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weddings", "0001_initial"),
        ("guests", "0001_initial"),
        ("invitations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeddingPhotoSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guest_upload_enabled", models.BooleanField(default=True)),
                ("moderation_required", models.BooleanField(default=True)),
                ("slideshow_enabled", models.BooleanField(default=False)),
                ("guest_can_download_own", models.BooleanField(default=True)),
                ("max_upload_mb", models.PositiveSmallIntegerField(default=15)),
                ("max_files_per_upload", models.PositiveSmallIntegerField(default=10)),
                ("slideshow_token", models.CharField(default=photos.models.generate_slideshow_token, editable=False, max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="photo_settings", to="weddings.wedding")),
            ],
            options={
                "verbose_name": "Wedding photo settings",
                "verbose_name_plural": "Wedding photo settings",
            },
        ),
        migrations.CreateModel(
            name="WeddingPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.CharField(default=photos.models.generate_photo_public_id, editable=False, max_length=20, unique=True)),
                ("source", models.CharField(choices=[("GUEST", "Guest"), ("STAFF", "Staff"), ("OWNER", "Owner")], default="GUEST", max_length=12)),
                ("image", models.FileField(upload_to=photos.models.photo_upload_to)),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("mime_type", models.CharField(blank=True, max_length=80)),
                ("file_size", models.PositiveBigIntegerField(default=0)),
                ("caption", models.CharField(blank=True, max_length=280)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="PENDING", max_length=12)),
                ("moderated_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("download_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("guest", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="photos", to="guests.guest")),
                ("invitation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="photos", to="invitations.invitation")),
                ("moderated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="moderated_wedding_photos", to=settings.AUTH_USER_MODEL)),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="uploaded_wedding_photos", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="weddings.wedding")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="weddingphoto",
            index=models.Index(fields=["wedding", "status", "-created_at"], name="photo_wed_status_idx"),
        ),
        migrations.AddIndex(
            model_name="weddingphoto",
            index=models.Index(fields=["wedding", "guest", "-created_at"], name="photo_wed_guest_idx"),
        ),
    ]
