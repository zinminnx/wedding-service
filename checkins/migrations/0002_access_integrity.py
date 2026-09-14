import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checkins", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="checkin",
            name="limit_overridden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="checkin",
            name="override_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="checkin",
            name="override_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="checkin_limit_overrides",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="checkin",
            name="override_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name="CheckInEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("ARRIVAL", "Arrival"), ("UNDO", "Undo"), ("OVERRIDE", "Limit Override")], max_length=16)),
                ("quantity_delta", models.SmallIntegerField()),
                ("resulting_count", models.PositiveSmallIntegerField(default=0)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("checkin", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="checkins.checkin")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="checkin_events_created", to=settings.AUTH_USER_MODEL)),
                ("guest", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checkin_events", to="guests.guest")),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checkin_events", to="weddings.wedding")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["wedding", "-created_at"], name="checkin_event_wed_time_idx"),
                    models.Index(fields=["guest", "-created_at"], name="checkin_event_guest_time_idx"),
                ],
            },
        ),
    ]
