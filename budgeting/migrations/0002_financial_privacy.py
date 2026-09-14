from django.db import migrations, models


def share_existing_planner_items(apps, schema_editor):
    BudgetItem = apps.get_model("budgeting", "BudgetItem")
    BudgetItem.objects.filter(source="PLANNER").update(visibility="SHARED")


class Migration(migrations.Migration):
    dependencies = [
        ("budgeting", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="budgetitem",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("PRIVATE", "Private to Owner / Manager"),
                    ("SHARED", "Shared with Planner"),
                ],
                db_index=True,
                default="PRIVATE",
                help_text="Private Couple expenses are hidden from Wedding Planner accounts.",
                max_length=16,
            ),
        ),
        migrations.RunPython(share_existing_planner_items, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="budgetitem",
            index=models.Index(fields=["wedding", "visibility"], name="budget_wed_vis_idx"),
        ),
    ]
