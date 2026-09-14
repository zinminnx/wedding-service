import django.db.models.deletion
import financial_docs.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("budgeting", "0002_financial_privacy"),
        ("vendors", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weddings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinancialAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(db_index=True, max_length=64)),
                ("entity_type", models.CharField(max_length=40)),
                ("entity_id", models.CharField(blank=True, max_length=64)),
                ("message", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="financial_audit_events", to=settings.AUTH_USER_MODEL)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_audit_events", to="weddings.wedding")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="FinancialDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_label", models.CharField(blank=True, max_length=220)),
                ("document_type", models.CharField(choices=[("RECEIPT", "Receipt"), ("INVOICE", "Invoice"), ("QUOTATION", "Quotation"), ("CONTRACT", "Contract"), ("PAYMENT_PROOF", "Payment Proof"), ("OTHER", "Other")], max_length=24)),
                ("title", models.CharField(max_length=180)),
                ("file", models.FileField(upload_to=financial_docs.models.financial_upload_to)),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("file_size", models.PositiveBigIntegerField(default=0)),
                ("visibility", models.CharField(choices=[("PRIVATE", "Private to Owner / Manager"), ("SHARED", "Shared with Planner")], db_index=True, default="PRIVATE", max_length=16)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("budget_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="financial_documents", to="budgeting.budgetitem")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="uploaded_financial_documents", to=settings.AUTH_USER_MODEL)),
                ("vendor_quote", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="financial_documents", to="vendors.vendorquote")),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_documents", to="weddings.wedding")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(model_name="financialauditevent", index=models.Index(fields=["wedding", "created_at"], name="finaudit_wed_time_idx")),
        migrations.AddIndex(model_name="financialdocument", index=models.Index(fields=["wedding", "document_type"], name="findoc_wed_type_idx")),
        migrations.AddIndex(model_name="financialdocument", index=models.Index(fields=["wedding", "visibility"], name="findoc_wed_vis_idx")),
    ]
