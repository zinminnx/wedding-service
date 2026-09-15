# EverVow v11.2: add Wedding Planner staff membership role.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("staffing", "0002_wedding_workspace_preference"),
    ]

    operations = [
        migrations.AlterField(
            model_name="weddingstaffmembership",
            name="role",
            field=models.CharField(
                choices=[
                    ("WEDDING_MANAGER", "Wedding Manager"),
                    ("WEDDING_PLANNER", "Wedding Planner"),
                    ("RECEPTION_STAFF", "Reception Staff"),
                    ("PHOTO_STAFF", "Photo Staff"),
                    ("PRINT_STAFF", "Print Staff"),
                    ("VIEWER", "Viewer"),
                ],
                max_length=32,
            ),
        ),
    ]
