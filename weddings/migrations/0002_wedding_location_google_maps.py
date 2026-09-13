from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("weddings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="wedding",
            name="wedding_location",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="wedding",
            name="google_maps_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
