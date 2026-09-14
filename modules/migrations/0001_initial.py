from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weddings", "0002_wedding_location_google_maps"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeatureModule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("version", models.CharField(default="1.0", max_length=32)),
                ("module_type", models.CharField(choices=[("CORE", "Core"), ("OPTIONAL", "Optional")], default="OPTIONAL", max_length=12)),
                ("system_enabled", models.BooleanField(default=True)),
                ("visible_to_weddings", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=100)),
                ("allowed_roles", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="ServicePackage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("modules", models.ManyToManyField(blank=True, related_name="service_packages", to="modules.featuremodule")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="featuremodule",
            name="dependencies",
            field=models.ManyToManyField(blank=True, related_name="dependent_modules", symmetrical=False, to="modules.featuremodule"),
        ),
        migrations.CreateModel(
            name="WeddingModuleProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("package", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="wedding_profiles", to="modules.servicepackage")),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="module_profile", to="weddings.wedding")),
            ],
        ),
        migrations.CreateModel(
            name="WeddingModuleSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wedding_settings", to="modules.featuremodule")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_wedding_module_settings", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="module_settings", to="weddings.wedding")),
            ],
        ),
        migrations.AddConstraint(
            model_name="weddingmodulesetting",
            constraint=models.UniqueConstraint(fields=("wedding", "module"), name="unique_wedding_module_setting"),
        ),
        migrations.AddIndex(
            model_name="weddingmodulesetting",
            index=models.Index(fields=["wedding", "enabled"], name="wed_module_enabled_idx"),
        ),
    ]
