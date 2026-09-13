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
            name="WeddingStaffMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("WEDDING_MANAGER", "Wedding Manager"), ("RECEPTION_STAFF", "Reception Staff"), ("PHOTO_STAFF", "Photo Staff"), ("PRINT_STAFF", "Print Staff"), ("VIEWER", "Viewer")], max_length=32)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")], default="ACTIVE", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_wedding_staff_memberships", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wedding_memberships", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="staff_memberships", to="weddings.wedding")),
            ],
            options={"ordering": ["role", "user__username"]},
        ),
        migrations.AddConstraint(
            model_name="weddingstaffmembership",
            constraint=models.UniqueConstraint(fields=("wedding", "user"), name="unique_wedding_staff_membership"),
        ),
        migrations.AddIndex(
            model_name="weddingstaffmembership",
            index=models.Index(fields=["wedding", "status"], name="staffing_we_wedding_32e9d8_idx"),
        ),
        migrations.AddIndex(
            model_name="weddingstaffmembership",
            index=models.Index(fields=["user", "status"], name="staffing_we_user_id_f0a219_idx"),
        ),
    ]
