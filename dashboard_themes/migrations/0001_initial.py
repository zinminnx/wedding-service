from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


BUILTIN_THEMES = [
    {
        "key": "everafter-classic",
        "name": "EverAfter Classic",
        "description": "Original dark navy, ivory and gold EverAfter dashboard.",
        "is_default": True,
        "sort_order": 10,
        "sidebar_bg": "#101827",
        "sidebar_text": "#F8FAFC",
        "content_bg": "#F7F3EA",
        "surface_bg": "#FFFFFF",
        "accent": "#C7A35A",
        "text_color": "#1F2937",
        "muted_color": "#6B7280",
        "border_color": "#E8E1D5",
    },
    {
        "key": "ivory-gold",
        "name": "Ivory & Gold",
        "description": "Light luxury palette with warm champagne accents.",
        "sort_order": 20,
        "sidebar_bg": "#2F2A23",
        "sidebar_text": "#FFFDF7",
        "content_bg": "#FBF7EF",
        "surface_bg": "#FFFFFF",
        "accent": "#B99045",
        "text_color": "#2D2924",
        "muted_color": "#7A7065",
        "border_color": "#E8DDCC",
    },
    {
        "key": "midnight-gold",
        "name": "Midnight Gold",
        "description": "Deep midnight workspace with richer gold contrast.",
        "sort_order": 30,
        "sidebar_bg": "#070B14",
        "sidebar_text": "#F8F5EC",
        "content_bg": "#111827",
        "surface_bg": "#182235",
        "accent": "#D4AF68",
        "text_color": "#F8FAFC",
        "muted_color": "#AAB4C5",
        "border_color": "#2D3A50",
    },
    {
        "key": "emerald-royal",
        "name": "Emerald Royal",
        "description": "Elegant emerald sidebar with soft stone surfaces.",
        "sort_order": 40,
        "sidebar_bg": "#103B34",
        "sidebar_text": "#F8FBF8",
        "content_bg": "#F4F7F2",
        "surface_bg": "#FFFFFF",
        "accent": "#B99755",
        "text_color": "#20332E",
        "muted_color": "#697B75",
        "border_color": "#DCE6E1",
    },
    {
        "key": "rose-champagne",
        "name": "Rose Champagne",
        "description": "Soft rose neutrals with refined champagne highlights.",
        "sort_order": 50,
        "sidebar_bg": "#4B3137",
        "sidebar_text": "#FFF8F8",
        "content_bg": "#FCF5F3",
        "surface_bg": "#FFFFFF",
        "accent": "#C59A67",
        "text_color": "#3B2D30",
        "muted_color": "#806D72",
        "border_color": "#EEDDDD",
    },
]


def seed_dashboard_themes(apps, schema_editor):
    DashboardTheme = apps.get_model("dashboard_themes", "DashboardTheme")
    FeatureModule = apps.get_model("modules", "FeatureModule")

    for spec in BUILTIN_THEMES:
        key = spec["key"]
        defaults = dict(spec)
        defaults.pop("key")
        defaults.setdefault("is_active", True)
        defaults.setdefault("heading_font", "Georgia, serif")
        defaults.setdefault("body_font", "Arial, sans-serif")
        defaults.setdefault("radius_px", 14)
        DashboardTheme.objects.update_or_create(key=key, defaults=defaults)

    FeatureModule.objects.update_or_create(
        key="dashboard_themes",
        defaults={
            "name": "Dashboard Themes",
            "description": "Per-user dashboard visual themes and layout density.",
            "version": "1.0",
            "module_type": "OPTIONAL",
            "system_enabled": True,
            "visible_to_weddings": False,
            "sort_order": 220,
            "allowed_roles": [],
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("modules", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardTheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_default", models.BooleanField(db_index=True, default=False)),
                ("sort_order", models.PositiveSmallIntegerField(default=100)),
                ("sidebar_bg", models.CharField(default="#111827", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("sidebar_text", models.CharField(default="#F8FAFC", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("content_bg", models.CharField(default="#F7F3EA", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("surface_bg", models.CharField(default="#FFFFFF", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("accent", models.CharField(default="#C9A35D", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("text_color", models.CharField(default="#1F2937", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("muted_color", models.CharField(default="#6B7280", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("border_color", models.CharField(default="#E5E0D8", max_length=7, validators=[django.core.validators.RegexValidator(message="Use a 6-digit hex color such as #0F172A.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("heading_font", models.CharField(default="Georgia, serif", max_length=120)),
                ("body_font", models.CharField(default="Arial, sans-serif", max_length=120)),
                ("radius_px", models.PositiveSmallIntegerField(default=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="UserDashboardPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("density", models.CharField(choices=[("COMFORTABLE", "Comfortable"), ("COMPACT", "Compact"), ("SPACIOUS", "Spacious")], default="COMFORTABLE", max_length=16)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("theme", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="user_preferences", to="dashboard_themes.dashboardtheme")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="dashboard_preference", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(seed_dashboard_themes, noop_reverse),
    ]
