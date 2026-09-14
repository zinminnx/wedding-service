from django.db import migrations, models


def copy_venue_to_wedding(apps, schema_editor):
    WeddingEventSettings = apps.get_model("event_tools", "WeddingEventSettings")
    for settings_obj in WeddingEventSettings.objects.select_related("wedding").all().iterator():
        wedding = settings_obj.wedding
        changed = []

        mapping = [
            ("wedding_location", "venue_name"),
            ("venue_full_address", "full_address"),
            ("venue_latitude", "latitude"),
            ("venue_longitude", "longitude"),
            ("venue_landmark", "landmark"),
            ("venue_location_note", "location_note"),
            ("google_maps_url", "google_maps_url"),
        ]
        for wedding_field, old_field in mapping:
            current = getattr(wedding, wedding_field, None)
            old_value = getattr(settings_obj, old_field, None)
            if (current is None or current == "") and old_value not in (None, ""):
                setattr(wedding, wedding_field, old_value)
                changed.append(wedding_field)

        if changed:
            wedding.save(update_fields=changed)


def reverse_noop(apps, schema_editor):
    # Venue data remains on Wedding if this migration is reversed.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("event_tools", "0001_initial"),
        ("weddings", "0003_venue_master_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="weddingeventsettings",
            name="smart_map_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="weddingeventsettings",
            name="show_address",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="weddingeventsettings",
            name="show_landmark",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="weddingeventsettings",
            name="show_location_note",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="weddingeventsettings",
            name="show_google_maps",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="weddingeventsettings",
            name="show_apple_maps",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(copy_venue_to_wedding, reverse_noop),
        migrations.RemoveField(model_name="weddingeventsettings", name="venue_name"),
        migrations.RemoveField(model_name="weddingeventsettings", name="full_address"),
        migrations.RemoveField(model_name="weddingeventsettings", name="latitude"),
        migrations.RemoveField(model_name="weddingeventsettings", name="longitude"),
        migrations.RemoveField(model_name="weddingeventsettings", name="landmark"),
        migrations.RemoveField(model_name="weddingeventsettings", name="location_note"),
        migrations.RemoveField(model_name="weddingeventsettings", name="google_maps_url"),
    ]
