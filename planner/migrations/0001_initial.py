# Generated for EverAfter v11.2 Wedding Planner Workspace

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weddings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlannerNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("body", models.TextField()),
                ("is_pinned", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_planner_notes", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="planner_notes", to="weddings.wedding")),
            ],
            options={"ordering": ["-is_pinned", "-updated_at"]},
        ),
        migrations.CreateModel(
            name="PlannerAppointment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("starts_at", models.DateTimeField(db_index=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("notes", models.TextField(blank=True)),
                ("reminder_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_planner_appointments", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_planner_appointments", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="planner_appointments", to="weddings.wedding")),
            ],
            options={"ordering": ["starts_at", "title"]},
        ),
        migrations.CreateModel(
            name="PlannerTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("kind", models.CharField(choices=[("TASK", "Task"), ("CHECKLIST", "Checklist"), ("MILESTONE", "Milestone")], db_index=True, default="TASK", max_length=16)),
                ("status", models.CharField(choices=[("TODO", "To do"), ("IN_PROGRESS", "In progress"), ("WAITING", "Waiting"), ("DONE", "Done"), ("CANCELLED", "Cancelled")], db_index=True, default="TODO", max_length=20)),
                ("priority", models.CharField(choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("URGENT", "Urgent")], db_index=True, default="NORMAL", max_length=12)),
                ("due_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("reminder_at", models.DateTimeField(blank=True, null=True)),
                ("sort_order", models.PositiveIntegerField(default=100)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_planner_tasks", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_planner_tasks", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="planner_tasks", to="weddings.wedding")),
            ],
            options={"ordering": ["status", "due_at", "sort_order", "title"]},
        ),
        migrations.CreateModel(
            name="RunSheetItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheduled_at", models.DateTimeField(db_index=True)),
                ("title", models.CharField(max_length=180)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("owner_label", models.CharField(blank=True, help_text="Person/team responsible, e.g. MC or Reception", max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("PLANNED", "Planned"), ("READY", "Ready"), ("DONE", "Done"), ("SKIPPED", "Skipped")], db_index=True, default="PLANNED", max_length=12)),
                ("sort_order", models.PositiveIntegerField(default=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_run_sheet_items", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="run_sheet_items", to="weddings.wedding")),
            ],
            options={"ordering": ["scheduled_at", "sort_order", "title"]},
        ),
        migrations.AddIndex(model_name="plannernote", index=models.Index(fields=["wedding", "is_pinned"], name="planner_note_pin_idx")),
        migrations.AddIndex(model_name="plannerappointment", index=models.Index(fields=["wedding", "starts_at"], name="planner_appt_time_idx")),
        migrations.AddIndex(model_name="plannertask", index=models.Index(fields=["wedding", "status"], name="planner_task_status_idx")),
        migrations.AddIndex(model_name="plannertask", index=models.Index(fields=["wedding", "due_at"], name="planner_task_due_idx")),
        migrations.AddIndex(model_name="runsheetitem", index=models.Index(fields=["wedding", "scheduled_at"], name="planner_run_time_idx")),
    ]
