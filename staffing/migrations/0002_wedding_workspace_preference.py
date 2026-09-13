from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("staffing", "0001_initial"),
        ("weddings", "0002_wedding_location_google_maps"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeddingWorkspacePreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("active_wedding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="weddings.wedding")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="wedding_workspace_preference", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
