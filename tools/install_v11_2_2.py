from pathlib import Path
import datetime
import re
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
PATCH_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = PATCH_ROOT / "payload"
BACKUP_ROOT = ROOT.parent / "_everafter_patch_backups" / ("v11_2_2_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def require(rel):
    path = ROOT / rel
    if not path.exists():
        raise SystemExit(f"Required file not found: {rel}. Install prerequisite patches first.")
    return path


def read(rel):
    return require(rel).read_text(encoding="utf-8-sig")


def backup(path):
    if not path.exists():
        return
    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def write(rel, text):
    path = ROOT / rel
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_tree(source, target):
    if not source.exists():
        raise SystemExit(f"Patch payload missing: {source}")
    for src in source.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(source)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            backup(dst)
        shutil.copy2(src, dst)
        print(f"Installed: {dst.relative_to(ROOT)}")


def patch_once(rel, marker, insertion, description):
    text = read(rel)
    if insertion.strip() in text:
        print(f"No change needed: {description}")
        return
    if marker not in text:
        raise SystemExit(f"Could not find safe patch marker in {rel}: {marker}")
    text = text.replace(marker, marker + insertion, 1)
    write(rel, text)
    print(f"Updated: {description}")


require("manage.py")
require("budgeting/models.py")
require("modules/services.py")
require("modules/middleware.py")
require("modules/management/commands/seed_modules.py")
require("staffing/models.py")
require("staffing/access.py")
require("weddings/templates/dashboard/base.html")
require("config/settings.py")
require("config/urls.py")

# 1) Restore the complete Planner app. This repairs the exact failure where
#    apply_patch.ps1 existed but planner/apps.py was never installed.
copy_tree(PAYLOAD / "planner", ROOT / "planner")

# 2) Add Wedding Planner to the membership role choices.
rel = "staffing/models.py"
text = read(rel)
if 'WEDDING_PLANNER = "WEDDING_PLANNER", "Wedding Planner"' not in text:
    marker = '        WEDDING_MANAGER = "WEDDING_MANAGER", "Wedding Manager"'
    if marker not in text:
        raise SystemExit("Could not find Wedding Manager role in staffing/models.py")
    text = text.replace(marker, marker + '\n        WEDDING_PLANNER = "WEDDING_PLANNER", "Wedding Planner"', 1)
    write(rel, text)
    print("Updated: staffing Wedding Planner role")
else:
    print("No change needed: staffing Wedding Planner role already present")

# 3) Ensure migration state records the choices change without creating a
#    conflicting branch if a previous partial v11.2 run already created it.
migrations_dir = ROOT / "staffing" / "migrations"
planner_migration_found = False
for p in sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.py")):
    try:
        body = p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        continue
    if 'WEDDING_PLANNER' in body and 'weddingstaffmembership' in body.lower():
        planner_migration_found = True
        print(f"No change needed: Planner staffing migration already exists ({p.name})")
        break

if not planner_migration_found:
    existing = sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.py"))
    if not existing:
        raise SystemExit("No staffing migrations found; cannot create a safe Planner migration.")
    latest = existing[-1]
    m = re.match(r"(\d{4})_(.+)\.py$", latest.name)
    if not m:
        raise SystemExit(f"Unexpected migration name: {latest.name}")
    next_num = f"{int(m.group(1)) + 1:04d}"
    dep_name = latest.stem
    new_name = f"{next_num}_add_wedding_planner_role.py"
    new_path = migrations_dir / new_name
    migration_text = f'''# EverAfter v11.2.2 repair: add Wedding Planner role choice.\n\nfrom django.db import migrations, models\n\n\nclass Migration(migrations.Migration):\n    dependencies = [\n        ("staffing", "{dep_name}"),\n    ]\n\n    operations = [\n        migrations.AlterField(\n            model_name="weddingstaffmembership",\n            name="role",\n            field=models.CharField(\n                choices=[\n                    ("WEDDING_MANAGER", "Wedding Manager"),\n                    ("WEDDING_PLANNER", "Wedding Planner"),\n                    ("RECEPTION_STAFF", "Reception Staff"),\n                    ("PHOTO_STAFF", "Photo Staff"),\n                    ("PRINT_STAFF", "Print Staff"),\n                    ("VIEWER", "Viewer"),\n                ],\n                max_length=32,\n            ),\n        ),\n    ]\n'''
    new_path.write_text(migration_text, encoding="utf-8")
    print(f"Installed: staffing\\migrations\\{new_name}")

# 4) Planner permission. Targeted edits preserve v10.5+ access integrity logic.
rel = "staffing/access.py"
text = read(rel)
original = text
if 'PERM_PLANNER = "planner"' not in text:
    marker = 'PERM_PRINT = "print"'
    if marker not in text:
        raise SystemExit("Could not find PERM_PRINT in staffing/access.py")
    text = text.replace(marker, marker + '\nPERM_PLANNER = "planner"', 1)

# Add planner to ALL_STAFF_ROLES only if the set exists and role isn't there.
all_roles_match = re.search(r"ALL_STAFF_ROLES\s*=\s*\{(?P<body>.*?)\n\}", text, re.S)
if not all_roles_match:
    raise SystemExit("Could not find ALL_STAFF_ROLES in staffing/access.py")
if 'WeddingStaffMembership.Role.WEDDING_PLANNER' not in all_roles_match.group('body'):
    body = all_roles_match.group('body')
    manager_line = '    WeddingStaffMembership.Role.WEDDING_MANAGER,'
    if manager_line not in body:
        raise SystemExit("Could not find Wedding Manager in ALL_STAFF_ROLES")
    body = body.replace(manager_line, manager_line + '\n    WeddingStaffMembership.Role.WEDDING_PLANNER,', 1)
    text = text[:all_roles_match.start('body')] + body + text[all_roles_match.end('body'):]

if 'PERM_PLANNER: {' not in text:
    marker = '    PERM_PRINT: {'
    start = text.find(marker)
    if start == -1:
        raise SystemExit("Could not find PERM_PRINT permission block")
    end = text.find('    },', start)
    if end == -1:
        raise SystemExit("Could not find end of PERM_PRINT permission block")
    end += len('    },')
    block = '\n    PERM_PLANNER: {\n        WeddingStaffMembership.Role.WEDDING_MANAGER,\n        WeddingStaffMembership.Role.WEDDING_PLANNER,\n    },'
    text = text[:end] + block + text[end:]

if 'WeddingStaffMembership.Role.WEDDING_PLANNER: "Wedding Planner",' not in text:
    marker = '        WeddingStaffMembership.Role.WEDDING_MANAGER: "Wedding Manager",'
    if marker not in text:
        raise SystemExit("Could not find access summary role labels")
    text = text.replace(marker, marker + '\n        WeddingStaffMembership.Role.WEDDING_PLANNER: "Wedding Planner",', 1)

if '"planner": has_wedding_permission(user, wedding, PERM_PLANNER),' not in text:
    marker = '        "print": has_wedding_permission(user, wedding, PERM_PRINT),'
    if marker not in text:
        raise SystemExit("Could not find access summary print permission")
    text = text.replace(marker, marker + '\n        "planner": has_wedding_permission(user, wedding, PERM_PLANNER),', 1)

if text != original:
    write(rel, text)
    print("Updated: staffing Planner permission")
else:
    print("No change needed: staffing Planner permission already present")

# 5) INSTALLED_APPS.
rel = "config/settings.py"
text = read(rel)
if re.search(r'^\s*["\']planner["\'],?\s*$', text, re.M) is None:
    anchors = ['    "budgeting",', '    "transportation",', '    "event_tools",']
    marker = next((item for item in anchors if item in text), None)
    if marker is None:
        raise SystemExit("Could not find safe INSTALLED_APPS anchor for planner")
    text = text.replace(marker, marker + '\n    "planner",', 1)
    write(rel, text)
    print("Updated: config/settings.py")
else:
    print("No change needed: planner already in INSTALLED_APPS")

# 6) URL registration.
rel = "config/urls.py"
text = read(rel)
if 'include("planner.urls")' not in text and "include('planner.urls')" not in text:
    marker = "urlpatterns = ["
    if marker not in text:
        raise SystemExit("Could not find urlpatterns in config/urls.py")
    text = text.replace(marker, marker + '\n    path("", include("planner.urls")),', 1)
    write(rel, text)
    print("Updated: config/urls.py")
else:
    print("No change needed: planner URLs already included")

# 7) Server-side module namespace gate.
rel = "modules/middleware.py"
text = read(rel)
if '"planner": "planner"' not in text:
    candidates = ['    "budgeting": "budgeting",', '    "transportation": "transportation",', '    "staffing": "staffing",']
    marker = next((item for item in candidates if item in text), None)
    if marker is None:
        raise SystemExit("Could not find NAMESPACE_MODULES insertion point")
    text = text.replace(marker, marker + '\n    "planner": "planner",', 1)
    write(rel, text)
    print("Updated: module middleware Planner gate")
else:
    print("No change needed: Planner middleware gate already present")

# 8) Registry: enable Planner, allow owner/manager/planner and depend on Budgeting.
rel = "modules/management/commands/seed_modules.py"
text = read(rel)
original = text
new_spec = 'dict(key="planner", name="Wedding Planner", description="Planner tasks, checklist, appointments, reminders, notes and wedding-day run sheet.", system_enabled=True, visible_to_weddings=True, sort_order=250, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "WEDDING_PLANNER"]),'
if 'key="planner"' not in text:
    raise SystemExit("Planner registry seed entry not found. Install v10.4 Module Registry first.")
text = re.sub(r'dict\(key="planner"[^\n]+\),', new_spec, text, count=1)
if '"planner": ["budgeting"]' not in text:
    dep_marker = 'DEPENDENCIES = {'
    if dep_marker not in text:
        raise SystemExit("DEPENDENCIES registry not found")
    text = text.replace(dep_marker, dep_marker + '\n    "planner": ["budgeting"],', 1)

m = re.search(r'current_keys\s*=\s*\{([^}]*)\}', text, re.S)
if m and '"planner"' not in m.group(1):
    body = m.group(1).rstrip()
    if body.strip() and not body.rstrip().endswith(','):
        body += ','
    body += ' "planner"'
    text = text[:m.start(1)] + body + text[m.end(1):]

if text != original:
    write(rel, text)
    print("Updated: Planner registry/dependency/default package")
else:
    print("No change needed: Planner registry already ready")

# 9) Sidebar navigation, without replacing the shared dashboard template.
rel = "weddings/templates/dashboard/base.html"
text = read(rel)
if "planner:dashboard" not in text:
    nav = '''            {% if access.planner and 'planner' in enabled_modules %}\n            <a class="nav-item {% if request.resolver_match.namespace == 'planner' %}active{% endif %}" href="{% url 'planner:dashboard' %}">Planner</a>\n            {% endif %}\n'''
    patterns = [
        r'(^\s*<a[^\n]+budgeting:dashboard[^\n]+Budget</a>\s*$)',
        r'(^\s*<a[^\n]+transportation:settings[^\n]+Transportation</a>\s*$)',
        r'(^\s*<a[^\n]+staffing:list[^\n]+Staff[^<]*</a>\s*$)',
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, text, re.M)
        if match:
            break
    if match:
        text = text[:match.end()] + "\n" + nav.rstrip("\n") + text[match.end():]
    else:
        marker = '<div class="sidebar-quote">'
        if marker not in text:
            raise SystemExit("Could not find safe Planner navigation anchor")
        text = text.replace(marker, nav + marker, 1)
    write(rel, text)
    print("Updated: dashboard Planner navigation")
else:
    print("No change needed: Planner navigation already present")

print(f"Backup created outside project: {BACKUP_ROOT}")
