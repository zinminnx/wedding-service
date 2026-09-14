from django.db import migrations, models


SECTION_KEYS = [
    "hero", "story", "event", "calendar", "venue", "maps", "transportation",
    "schedule", "rsvp", "photos", "gift", "entry_pass", "gallery",
]
DEFAULT_ENABLED = {"hero", "event", "rsvp", "photos", "gift", "entry_pass", "gallery"}


def default_config():
    return [
        {"key": key, "enabled": key in DEFAULT_ENABLED, "sort_order": index * 10}
        for index, key in enumerate(SECTION_KEYS, start=1)
    ]


def seed_sections(apps, schema_editor):
    Theme = apps.get_model("invitation_themes", "InvitationTheme")
    Design = apps.get_model("invitation_themes", "WeddingInvitationDesign")

    for theme in Theme.objects.all().iterator():
        supported = list(theme.supported_sections or [])
        changed = False
        for key in SECTION_KEYS:
            if key not in supported:
                supported.append(key)
                changed = True
        if changed:
            theme.supported_sections = supported
            theme.save(update_fields=["supported_sections"])

    baseline = default_config()
    for design in Design.objects.all().iterator():
        updates = []
        if not design.draft_sections:
            design.draft_sections = list(baseline)
            updates.append("draft_sections")
        if design.published_theme_id and not design.published_sections:
            design.published_sections = list(baseline)
            updates.append("published_sections")
        if updates:
            design.save(update_fields=updates)


def reverse_seed(apps, schema_editor):
    # Do not destructively clear section choices on rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("invitation_themes", "0002_seed_themes"),
    ]

    operations = [
        migrations.AddField(
            model_name="weddinginvitationdesign",
            name="draft_sections",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="weddinginvitationdesign",
            name="published_sections",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(seed_sections, reverse_seed),
    ]
