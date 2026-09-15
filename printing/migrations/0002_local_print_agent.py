from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("printing", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PrintAgentDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("token_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("token_prefix", models.CharField(max_length=16)),
                ("enabled", models.BooleanField(default=True)),
                ("printer_name", models.CharField(blank=True, max_length=200)),
                ("hostname", models.CharField(blank=True, max_length=120)),
                ("agent_version", models.CharField(blank=True, max_length=40)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_print_agents", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="print_agent_devices", to="weddings.wedding")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddIndex(
            model_name="printagentdevice",
            index=models.Index(fields=["wedding", "enabled"], name="print_agent_wed_enabled_idx"),
        ),
        migrations.AddIndex(
            model_name="printagentdevice",
            index=models.Index(fields=["wedding", "last_seen_at"], name="print_agent_wed_seen_idx"),
        ),
        migrations.AddField(
            model_name="printjob",
            name="agent_device",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="jobs", to="printing.printagentdevice"),
        ),
        migrations.AddField(
            model_name="printjob",
            name="claim_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
