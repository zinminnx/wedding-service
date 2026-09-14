import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import invitation_themes.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("weddings", "0002_wedding_location_google_maps"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InvitationTheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("key", models.SlugField(max_length=64, unique=True)),
                ("category", models.CharField(choices=[("CLASSIC", "Classic"), ("MODERN", "Modern"), ("FLORAL", "Floral"), ("LUXURY", "Luxury"), ("ROMANTIC", "Romantic"), ("PHOTO", "Photo"), ("TRADITIONAL", "Traditional"), ("EDITORIAL", "Editorial"), ("ROYAL", "Royal"), ("ELEGANT", "Elegant")], default="CLASSIC", max_length=24)),
                ("description", models.TextField(blank=True)),
                ("preview_image", models.FileField(blank=True, null=True, upload_to=invitation_themes.models.preview_upload_to)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PUBLISHED", "Published"), ("DISABLED", "Disabled")], db_index=True, default="DRAFT", max_length=16)),
                ("visible", models.BooleanField(default=False)),
                ("featured", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=100)),
                ("is_default", models.BooleanField(default=False)),
                ("version", models.CharField(default="1.0", max_length=32)),
                ("layout_key", models.SlugField(default="classic", max_length=64)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("allowed_customization", models.JSONField(blank=True, default=list)),
                ("supported_sections", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.AddIndex(
            model_name="invitationtheme",
            index=models.Index(fields=["status", "visible", "sort_order"], name="invtheme_status_vis_idx"),
        ),
        migrations.CreateModel(
            name="WeddingInvitationDesign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("draft_customization", models.JSONField(blank=True, default=dict)),
                ("published_customization", models.JSONField(blank=True, default=dict)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("draft_theme", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="draft_wedding_designs", to="invitation_themes.invitationtheme")),
                ("published_theme", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="published_wedding_designs", to="invitation_themes.invitationtheme")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_invitation_designs", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="invitation_design", to="weddings.wedding")),
            ],
            options={"verbose_name": "Wedding invitation design", "verbose_name_plural": "Wedding invitation designs"},
        ),
    ]
