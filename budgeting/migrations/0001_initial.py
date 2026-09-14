from django.db import migrations, models
import django.db.models.deletion


DEFAULT_CATEGORIES = [
    "Venue",
    "Catering",
    "Decoration",
    "Photography",
    "Video",
    "Dress & Attire",
    "Rings",
    "Makeup & Beauty",
    "Entertainment",
    "Invitations & Printing",
    "Transportation",
    "Accommodation",
    "Gifts",
    "Planner Fee",
    "Miscellaneous",
]


def activate_budgeting(apps, schema_editor):
    FeatureModule = apps.get_model("modules", "FeatureModule")
    ServicePackage = apps.get_model("modules", "ServicePackage")
    Wedding = apps.get_model("weddings", "Wedding")
    BudgetCategory = apps.get_model("budgeting", "BudgetCategory")
    WeddingBudgetSettings = apps.get_model("budgeting", "WeddingBudgetSettings")

    module, _ = FeatureModule.objects.update_or_create(
        key="budgeting",
        defaults={
            "name": "Budgeting",
            "description": "Couple budget, estimates, committed costs, payments and financial summary.",
            "version": "1.0",
            "module_type": "OPTIONAL",
            "system_enabled": True,
            "visible_to_weddings": True,
            "sort_order": 240,
            "allowed_roles": ["WEDDING_OWNER", "WEDDING_MANAGER", "WEDDING_PLANNER"],
        },
    )
    package = ServicePackage.objects.filter(is_active=True, is_default=True).first()
    if package:
        package.modules.add(module)

    for wedding in Wedding.objects.all().only("pk"):
        WeddingBudgetSettings.objects.get_or_create(wedding_id=wedding.pk)
        existing = set(
            BudgetCategory.objects.filter(wedding_id=wedding.pk).values_list("name", flat=True)
        )
        to_create = []
        for index, name in enumerate(DEFAULT_CATEGORIES, start=1):
            if name not in existing:
                to_create.append(
                    BudgetCategory(wedding_id=wedding.pk, name=name, sort_order=index * 10)
                )
        if to_create:
            BudgetCategory.objects.bulk_create(to_create, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    # Disabling/removing a feature must never delete financial data.
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("modules", "0001_initial"),
        ("weddings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BudgetCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("sort_order", models.PositiveSmallIntegerField(default=100)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="budget_categories", to="weddings.wedding")),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="WeddingBudgetSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_budget", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("currency", models.CharField(default="MMK", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("wedding", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="budget_settings", to="weddings.wedding")),
            ],
            options={"verbose_name": "Wedding budget settings", "verbose_name_plural": "Wedding budget settings"},
        ),
        migrations.CreateModel(
            name="BudgetItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("source", models.CharField(choices=[("COUPLE", "Couple Budget"), ("PLANNER", "Planner Budget")], db_index=True, default="COUPLE", max_length=16)),
                ("status", models.CharField(choices=[("PLANNED", "Planned"), ("COMMITTED", "Committed"), ("IN_PROGRESS", "In progress"), ("COMPLETE", "Complete"), ("CANCELLED", "Cancelled")], db_index=True, default="PLANNED", max_length=20)),
                ("estimated_amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("committed_amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("paid_amount", models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ("final_actual_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="budgeting.budgetcategory")),
                ("wedding", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="budget_items", to="weddings.wedding")),
            ],
            options={
                "ordering": ["category__sort_order", "category__name", "title"],
                "indexes": [
                    models.Index(fields=["wedding", "source"], name="budget_wed_source_idx"),
                    models.Index(fields=["wedding", "status"], name="budget_wed_status_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="budgetcategory",
            constraint=models.UniqueConstraint(fields=("wedding", "name"), name="unique_budget_category_per_wedding"),
        ),
        migrations.RunPython(activate_budgeting, noop_reverse),
    ]
