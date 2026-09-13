from pathlib import Path
import re
import shutil

ROOT = Path.cwd()
PATCH_ROOT = Path(__file__).resolve().parent
PAYLOAD = PATCH_ROOT / "payload"


def require(path: Path):
    if not path.exists():
        raise SystemExit(f"Required project file not found: {path}. Run this patch from the wedding-service project root.")


def backup(path: Path):
    if not path.exists():
        return
    backup_path = path.with_suffix(path.suffix + ".v10_3.bak")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)
        print(f"Backup: {backup_path.relative_to(ROOT)}")


def copy_file(relative: str):
    source = PAYLOAD / relative
    target = ROOT / relative
    require(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup(target)
    shutil.copy2(source, target)
    print(f"Updated: {relative}")


def latest_migration(app: str):
    migrations_dir = ROOT / app / "migrations"
    require(migrations_dir)
    existing = sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.py"))
    if not existing:
        raise SystemExit(f"No existing {app} migration found")
    return existing[-1]


require(ROOT / "manage.py")
require(ROOT / "staffing" / "models.py")
require(ROOT / "weddings" / "static" / "weddings" / "css" / "dashboard.css")

# 1) Add a lightweight per-user selected-workspace preference model.
models_path = ROOT / "staffing" / "models.py"
models_text = models_path.read_text(encoding="utf-8")
if "class WeddingWorkspacePreference" not in models_text:
    backup(models_path)
    addition = '''\n\nclass WeddingWorkspacePreference(models.Model):\n    user = models.OneToOneField(\n        settings.AUTH_USER_MODEL,\n        on_delete=models.CASCADE,\n        related_name="wedding_workspace_preference",\n    )\n    active_wedding = models.ForeignKey(\n        "weddings.Wedding",\n        on_delete=models.SET_NULL,\n        null=True,\n        blank=True,\n        related_name="+",\n    )\n    updated_at = models.DateTimeField(auto_now=True)\n\n    def __str__(self):\n        return f"{self.user} -> {self.active_wedding or 'No wedding selected'}"\n'''
    models_path.write_text(models_text.rstrip() + addition + "\n", encoding="utf-8")
    print("Updated: staffing/models.py")
else:
    print("No change needed: WeddingWorkspacePreference already exists")

# 2) Create a migration for the preference model, only once.
staffing_migrations = ROOT / "staffing" / "migrations"
existing = sorted(staffing_migrations.glob("[0-9][0-9][0-9][0-9]_*.py"))
has_preference_migration = any(
    "WeddingWorkspacePreference" in p.read_text(encoding="utf-8", errors="ignore")
    for p in existing
)
if not has_preference_migration:
    latest_staffing = latest_migration("staffing")
    latest_weddings = latest_migration("weddings")
    match = re.match(r"(\d{4})_", latest_staffing.name)
    if not match:
        raise SystemExit(f"Could not understand migration name: {latest_staffing.name}")
    next_number = int(match.group(1)) + 1
    migration_path = staffing_migrations / f"{next_number:04d}_wedding_workspace_preference.py"
    migration_text = f'''from django.conf import settings\nfrom django.db import migrations, models\nimport django.db.models.deletion\n\n\nclass Migration(migrations.Migration):\n\n    dependencies = [\n        migrations.swappable_dependency(settings.AUTH_USER_MODEL),\n        ("staffing", "{latest_staffing.stem}"),\n        ("weddings", "{latest_weddings.stem}"),\n    ]\n\n    operations = [\n        migrations.CreateModel(\n            name="WeddingWorkspacePreference",\n            fields=[\n                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),\n                ("updated_at", models.DateTimeField(auto_now=True)),\n                ("active_wedding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="weddings.wedding")),\n                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="wedding_workspace_preference", to=settings.AUTH_USER_MODEL)),\n            ],\n        ),\n    ]\n'''
    migration_path.write_text(migration_text, encoding="utf-8")
    print(f"Created: staffing/migrations/{migration_path.name}")
else:
    print("No change needed: workspace preference migration already exists")

# 3) Install multi-workspace aware access helper and screens.
for relative in [
    "staffing/access.py",
    "staffing/templatetags/staffing_tags.py",
    "weddings/views.py",
    "weddings/urls.py",
    "weddings/templates/dashboard/base.html",
    "weddings/templates/dashboard/home.html",
    "weddings/templates/dashboard/wedding_list.html",
]:
    copy_file(relative)

# 4) Append isolated styles so v10.1/v10.2 wedding editor styling remains untouched.
css_path = ROOT / "weddings" / "static" / "weddings" / "css" / "dashboard.css"
css_text = css_path.read_text(encoding="utf-8")
styles = (PATCH_ROOT / "multi_wedding_styles.css").read_text(encoding="utf-8")
marker = "/* EverAfter v10.3 - Multi Wedding Workspaces */"
if marker not in css_text:
    backup(css_path)
    css_path.write_text(css_text.rstrip() + "\n\n" + styles.rstrip() + "\n", encoding="utf-8")
    print("Updated: weddings/static/weddings/css/dashboard.css (multi-wedding styles appended)")
else:
    print("No change needed: v10.3 styles already installed")

print("EverAfter v10.3 Multi-Wedding Workspaces installed successfully.")
