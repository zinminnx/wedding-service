from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("weddings", "0002_wedding_location_google_maps"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeddingEventSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("calendar_enabled", models.BooleanField(default=True)),
                ("calendar_title", models.CharField(blank=True, max_length=180)),
                ("calendar_description", models.TextField(blank=True)),
                ("event_duration_minutes", models.PositiveSmallIntegerField(default=240)),
                ("reminder_1_minutes", models.PositiveIntegerField(default=10080)),
                ("reminder_2_minutes", models.PositiveIntegerField(default=1440)),
                ("reminder_3_minutes", models.PositiveIntegerField(default=180)),
                ("venue_enabled", models.BooleanField(default=True)),
                ("venue_name", models.CharField(blank=True, max_length=180)),
                ("full_address", models.CharField(blank=True, max_length=500)),
                ("latitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ("landmark", models.CharField(blank=True, max_length=255)),
                ("location_note", models.TextField(blank=True)),
                ("google_maps_url", models.URLField(blank=True, max_length=1200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="event_tools_settings", to="weddings.wedding")),
            ],
            options={
                "verbose_name": "Wedding event settings",
                "verbose_name_plural": "Wedding event settings",
            },
        ),
    ]
