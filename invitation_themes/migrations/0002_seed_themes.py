from django.db import migrations


SECTIONS = ["hero", "event", "calendar", "venue", "transportation", "rsvp", "gift", "photos"]
CUSTOM = ["accent", "hero_message"]

THEMES = [
    ("ivory-gold-classic", "Ivory & Gold Classic", "CLASSIC", "classic", "#B98A45", "#FBF7EF", "Timeless ivory, warm gold and elegant serif details.", True, True, 10),
    ("modern-minimal", "Modern Minimal", "MODERN", "minimal", "#20252A", "#FFFFFF", "Clean whitespace, sharp typography and quiet modern structure.", False, True, 20),
    ("floral-garden", "Floral Garden", "FLORAL", "garden", "#718A6D", "#F5F1EA", "Soft botanical framing and garden-inspired cards.", False, True, 30),
    ("dark-luxury", "Dark Luxury", "LUXURY", "dark", "#D7B878", "#101214", "Cinematic charcoal, gold lines and dramatic contrast.", False, True, 40),
    ("pastel-romance", "Pastel Romance", "ROMANTIC", "pastel", "#C78798", "#FFF3F5", "Blush pastels, rounded details and romantic softness.", False, False, 50),
    ("photo-hero", "Photo Hero", "PHOTO", "photo", "#E4C99A", "#1B2024", "Large visual hero treatment with bold overlay typography.", False, True, 60),
    ("myanmar-traditional", "Myanmar Traditional", "TRADITIONAL", "myanmar", "#D5A84F", "#7C1F26", "Deep lacquer red and ceremonial gold inspired by Myanmar celebration styling.", False, True, 70),
    ("black-white-editorial", "Black & White Editorial", "EDITORIAL", "editorial", "#111111", "#FAFAF8", "High-contrast editorial type, rules and magazine-like spacing.", False, False, 80),
    ("emerald-royal", "Emerald Royal", "ROYAL", "emerald", "#D6B56D", "#0F4538", "Emerald panels, refined gold accents and formal symmetry.", False, True, 90),
    ("champagne-elegance", "Champagne Elegance", "ELEGANT", "champagne", "#A98255", "#F4E7D2", "Warm champagne layers, translucent cards and polished elegance.", False, False, 100),
]


def seed(apps, schema_editor):
    Theme = apps.get_model("invitation_themes", "InvitationTheme")
    for key, name, category, layout, accent, background, description, is_default, featured, order in THEMES:
        Theme.objects.update_or_create(
            key=key,
            defaults={
                "name": name,
                "category": category,
                "description": description,
                "status": "PUBLISHED",
                "visible": True,
                "featured": featured,
                "sort_order": order,
                "is_default": is_default,
                "version": "1.0",
                "layout_key": layout,
                "config": {"accent": accent, "background": background},
                "allowed_customization": CUSTOM,
                "supported_sections": SECTIONS,
            },
        )

    try:
        FeatureModule = apps.get_model("modules", "FeatureModule")
        ServicePackage = apps.get_model("modules", "ServicePackage")
        module = FeatureModule.objects.filter(key="invitation_themes").first()
        invitations = FeatureModule.objects.filter(key="invitations").first()
        if module:
            module.system_enabled = True
            module.visible_to_weddings = True
            module.version = "1.0"
            module.allowed_roles = ["WEDDING_OWNER"]
            module.save(update_fields=["system_enabled", "visible_to_weddings", "version", "allowed_roles", "updated_at"])
            if invitations:
                module.dependencies.set([invitations])
            package = ServicePackage.objects.filter(slug="standard").first()
            if package:
                package.modules.add(module)
    except LookupError:
        pass


def reverse_seed(apps, schema_editor):
    # Keep data on rollback to avoid breaking already-published wedding invitations.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("invitation_themes", "0001_initial"),
        ("modules", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, reverse_seed),
    ]
