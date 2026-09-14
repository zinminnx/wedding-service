from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("budgeting", "0001_initial"),
        ("weddings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Vendor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("contact_person", models.CharField(blank=True, max_length=120)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("website", models.URLField(blank=True)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")], db_index=True, default="ACTIVE", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="vendors", to="budgeting.budgetcategory")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_wedding_vendors", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vendors", to="weddings.wedding")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="VendorQuote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("comparison_group", models.CharField(blank=True, help_text="Use the same group name for alternative quotes, e.g. Photographer.", max_length=120)),
                ("quoted_amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("deposit_amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("final_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PROPOSED", "Proposed to Owner"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("WITHDRAWN", "Withdrawn")], db_index=True, default="DRAFT", max_length=16)),
                ("proposed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_budget_item", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="vendor_quote", to="budgeting.budgetitem")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vendor_quotes", to="budgeting.budgetcategory")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_vendor_quotes", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_vendor_quotes", to=settings.AUTH_USER_MODEL)),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quotes", to="vendors.vendor")),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vendor_quotes", to="weddings.wedding")),
            ],
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="vendor",
            index=models.Index(fields=["wedding", "status"], name="vendor_wed_status_idx"),
        ),
        migrations.AddIndex(
            model_name="vendorquote",
            index=models.Index(fields=["wedding", "status"], name="quote_wed_status_idx"),
        ),
        migrations.AddIndex(
            model_name="vendorquote",
            index=models.Index(fields=["wedding", "comparison_group"], name="quote_wed_group_idx"),
        ),
    ]
