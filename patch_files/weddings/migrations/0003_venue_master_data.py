from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("weddings", "0002_wedding_location_google_maps"),
    ]

    operations = [
        migrations.AddField(
            model_name="wedding",
            name="venue_full_address",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="wedding",
            name="venue_latitude",
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="wedding",
            name="venue_longitude",
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="wedding",
            name="venue_landmark",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="wedding",
            name="venue_location_note",
            field=models.TextField(blank=True),
        ),
    ]
