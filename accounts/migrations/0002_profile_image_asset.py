from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfileImageAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("drive_id", models.CharField(max_length=180)),
                ("remote_item_id", models.CharField(db_index=True, max_length=255)),
                ("remote_path", models.CharField(max_length=700)),
                ("remote_web_url", models.URLField(blank=True, max_length=1000)),
                ("mime_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("sha256", models.CharField(blank=True, db_index=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile_image_asset", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["user_id"]},
        ),
    ]
