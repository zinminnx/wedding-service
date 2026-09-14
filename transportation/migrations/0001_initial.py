from django.db import migrations, models
import django.db.models.deletion


def activate_transportation_module(apps, schema_editor):
    FeatureModule = apps.get_model("modules", "FeatureModule")
    ServicePackage = apps.get_model("modules", "ServicePackage")

    module, _ = FeatureModule.objects.update_or_create(
        key="transportation",
        defaults={
            "name": "Transportation",
            "description": "Guest travel guidance, maps and Bus Project provider integration.",
            "version": "1.0",
            "module_type": "OPTIONAL",
            "system_enabled": True,
            "visible_to_weddings": True,
            "sort_order": 230,
            "allowed_roles": ["WEDDING_OWNER", "WEDDING_MANAGER"],
        },
    )
    invitations = FeatureModule.objects.filter(key="invitations").first()
    if invitations:
        module.dependencies.add(invitations)

    package = ServicePackage.objects.filter(is_active=True, is_default=True).first()
    if package:
        package.modules.add(module)


def noop_reverse(apps, schema_editor):
    # Feature disable/uninstall must never delete wedding data.
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("modules", "0001_initial"),
        ("weddings", "0003_venue_master_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeddingTransportationSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guide_enabled", models.BooleanField(default=True)),
                ("bus_guide_enabled", models.BooleanField(default=False)),
                ("provider", models.CharField(choices=[("MANUAL", "Manual guidance only"), ("BUS_PROJECT", "Bus Project API (adapter-ready)")], default="MANUAL", max_length=24)),
                ("transport_note", models.TextField(blank=True)),
                ("fallback_message", models.CharField(default="Bus route information is temporarily unavailable. Please use the map and venue details above.", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="transportation_settings", to="weddings.wedding")),
            ],
            options={
                "verbose_name": "Wedding transportation settings",
                "verbose_name_plural": "Wedding transportation settings",
            },
        ),
        migrations.RunPython(activate_transportation_module, noop_reverse),
    ]
