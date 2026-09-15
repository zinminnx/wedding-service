from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
        ("invitation_themes", "0003_invitation_section_builder"),
    ]

    operations = [
        migrations.AddField(
            model_name="weddinginvitationdesign",
            name="draft_hero_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="integrations.storedobject",
            ),
        ),
        migrations.AddField(
            model_name="weddinginvitationdesign",
            name="published_hero_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="integrations.storedobject",
            ),
        ),
    ]
