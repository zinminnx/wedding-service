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
    b = path.with_suffix(path.suffix + ".v10_2.bak")
    if path.exists() and not b.exists():
        shutil.copy2(path, b)
        print(f"Backup: {b}")


def copy_file(relative: str):
    source = PAYLOAD / relative
    target = ROOT / relative
    require(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup(target)
    shutil.copy2(source, target)
    print(f"Updated: {relative}")


require(ROOT / "manage.py")
models_path = ROOT / "weddings" / "models.py"
require(models_path)
require(ROOT / "weddings" / "migrations")
require(ROOT / "weddings" / "static" / "weddings" / "css" / "dashboard.css")

# Add model fields without replacing the rest of the Wedding model.
models_text = models_path.read_text(encoding="utf-8")
changed_models = False
if "wedding_location =" not in models_text:
    pattern = re.compile(r"^(\s*)guest_limit\s*=", re.MULTILINE)
    match = pattern.search(models_text)
    if not match:
        raise SystemExit("Could not find Wedding.guest_limit in weddings/models.py")
    indent = match.group(1)
    insertion = (
        f'{indent}wedding_location = models.CharField(max_length=255, blank=True)\n'
        f'{indent}google_maps_url = models.URLField(max_length=1000, blank=True)\n\n'
    )
    models_text = models_text[:match.start()] + insertion + models_text[match.start():]
    changed_models = True
elif "google_maps_url =" not in models_text:
    line = re.search(r"^(\s*)wedding_location\s*=.*$", models_text, re.MULTILINE)
    if not line:
        raise SystemExit("Could not place google_maps_url in weddings/models.py")
    indent = line.group(1)
    models_text = models_text[:line.end()] + f'\n{indent}google_maps_url = models.URLField(max_length=1000, blank=True)' + models_text[line.end():]
    changed_models = True

if changed_models:
    backup(models_path)
    models_path.write_text(models_text, encoding="utf-8")
    print("Updated: weddings/models.py")
else:
    print("No change needed: Wedding location fields already exist")

copy_file("weddings/forms.py")
copy_file("weddings/templates/dashboard/wedding_overview.html")
copy_file("weddings/static/weddings/js/wedding-editor.js")

# Append isolated styles so older premium dashboard styles stay intact.
css_path = ROOT / "weddings" / "static" / "weddings" / "css" / "dashboard.css"
css = css_path.read_text(encoding="utf-8")
styles = (PATCH_ROOT / "location_styles.css").read_text(encoding="utf-8")
marker = "/* EverAfter v10.2 - Wedding Location + Google Maps */"
if marker not in css:
    backup(css_path)
    css_path.write_text(css.rstrip() + "\n\n" + styles.rstrip() + "\n", encoding="utf-8")
    print("Updated: weddings/static/weddings/css/dashboard.css (location styles appended)")
else:
    print("No change needed: v10.2 styles already installed")

# Create a migration only if a location migration does not already exist.
migrations_dir = ROOT / "weddings" / "migrations"
existing = sorted(p for p in migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.py"))
has_location_migration = any(
    "wedding_location" in p.read_text(encoding="utf-8", errors="ignore") and
    "google_maps_url" in p.read_text(encoding="utf-8", errors="ignore")
    for p in existing
)
if not has_location_migration:
    if not existing:
        raise SystemExit("No existing weddings migration found")
    latest = existing[-1]
    m = re.match(r"(\d{4})_(.+)\.py$", latest.name)
    if not m:
        raise SystemExit(f"Could not understand migration name: {latest.name}")
    next_number = int(m.group(1)) + 1
    migration_name = f"{next_number:04d}_wedding_location_google_maps.py"
    migration_path = migrations_dir / migration_name
    dep_name = latest.stem
    migration_text = f'''from django.db import migrations, models\n\n\nclass Migration(migrations.Migration):\n\n    dependencies = [\n        ("weddings", "{dep_name}"),\n    ]\n\n    operations = [\n        migrations.AddField(\n            model_name="wedding",\n            name="wedding_location",\n            field=models.CharField(blank=True, max_length=255),\n        ),\n        migrations.AddField(\n            model_name="wedding",\n            name="google_maps_url",\n            field=models.URLField(blank=True, max_length=1000),\n        ),\n    ]\n'''
    migration_path.write_text(migration_text, encoding="utf-8")
    print(f"Created: weddings/migrations/{migration_name}")
else:
    print("No change needed: location migration already exists")

# Bump CSS cache key while preserving the rest of base.html.
base_path = ROOT / "weddings" / "templates" / "dashboard" / "base.html"
if base_path.exists():
    base = base_path.read_text(encoding="utf-8")
    updated = re.sub(r"dashboard\.css' %\}\?v=[^\"']+", "dashboard.css' %}?v=10.2", base, count=1)
    if updated != base:
        backup(base_path)
        base_path.write_text(updated, encoding="utf-8")
        print("Updated: dashboard.css cache key")

print("EverAfter v10.2 Wedding Location + Google Maps installed successfully.")
