from pathlib import Path
import datetime
import re
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
PATCH_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = PATCH_ROOT / "payload"
BACKUP_ROOT = ROOT.parent / "_everafter_patch_backups" / ("v11_2_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


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


require("manage.py")
require("budgeting/models.py")
require("modules/services.py")
require("modules/middleware.py")
require("modules/management/commands/seed_modules.py")
require("staffing/models.py")
require("staffing/access.py")
require("staffing/migrations/0002_wedding_workspace_preference.py")
require("weddings/templates/dashboard/base.html")

copy_tree(PAYLOAD / "planner", ROOT / "planner")

# Add staffing migration safely.
staff_migration = ROOT / "staffing/migrations/0003_add_wedding_planner_role.py"
other_0003 = [p for p in (ROOT / "staffing/migrations").glob("0003*.py") if p.name != staff_migration.name]
if other_0003 and not staff_migration.exists():
    names = ", ".join(p.name for p in other_0003)
    raise SystemExit(f"Unexpected staffing 0003 migration already exists ({names}). Stop and report this before continuing.")
if not staff_migration.exists():
    src = PAYLOAD / "staffing/migrations/0003_add_wedding_planner_role.py"
    staff_migration.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, staff_migration)
    print("Installed: staffing\\migrations\\0003_add_wedding_planner_role.py")

# Patch membership role without replacing staffing models.
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
    print("No change needed: Wedding Planner role already present")

# Patch planner permission in the v10.5+ access model using targeted edits.
rel = "staffing/access.py"
text = read(rel)
original = text
if 'PERM_PLANNER = "planner"' not in text:
    marker = 'PERM_PRINT = "print"'
    if marker not in text:
        raise SystemExit("Could not find PERM_PRINT in staffing/access.py")
    text = text.replace(marker, marker + '\nPERM_PLANNER = "planner"', 1)
if 'WeddingStaffMembership.Role.WEDDING_PLANNER,' not in text:
    marker = '    WeddingStaffMembership.Role.WEDDING_MANAGER,'
    if marker not in text:
        raise SystemExit("Could not find ALL_STAFF_ROLES insertion point")
    text = text.replace(marker, marker + '\n    WeddingStaffMembership.Role.WEDDING_PLANNER,', 1)
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
        raise SystemExit("Could not find planner role label insertion point")
    text = text.replace(marker, marker + '\n        WeddingStaffMembership.Role.WEDDING_PLANNER: "Wedding Planner",', 1)
if '"planner": has_wedding_permission(user, wedding, PERM_PLANNER),' not in text:
    marker = '        "print": has_wedding_permission(user, wedding, PERM_PRINT),'
    if marker not in text:
        raise SystemExit("Could not find access summary print permission")
    text = text.replace(marker, marker + '\n        "planner": has_wedding_permission(user, wedding, PERM_PLANNER),', 1)
if text != original:
    write(rel, text)
    print("Updated: staffing planner permission")
else:
    print("No change needed: staffing planner permission already present")

# Register app.
rel = "config/settings.py"
text = read(rel)
if re.search(r'^\s*["\']planner["\'],?\s*$', text, re.M) is None:
    anchors = ['    "budgeting",', '    "transportation",', '    "event_tools",']
    marker = next((item for item in anchors if item in text), None)
    if marker is None:
        raise SystemExit("Could not find a safe INSTALLED_APPS anchor for planner.")
    text = text.replace(marker, marker + '\n    "planner",', 1)
    write(rel, text)
    print("Updated: config/settings.py")
else:
    print("No change needed: planner already in INSTALLED_APPS")

# Register URLs.
rel = "config/urls.py"
text = read(rel)
if 'include("planner.urls")' not in text:
    marker = "urlpatterns = ["
    if marker not in text:
        raise SystemExit("Could not find urlpatterns in config/urls.py")
    text = text.replace(marker, marker + '\n    path("", include("planner.urls")),', 1)
    write(rel, text)
    print("Updated: config/urls.py")
else:
    print("No change needed: planner URLs already included")

# Server-side module gate.
rel = "modules/middleware.py"
text = read(rel)
if '"planner": "planner"' not in text:
    candidates = ['    "budgeting": "budgeting",', '    "transportation": "transportation",', '    "staffing": "staffing",']
    marker = next((item for item in candidates if item in text), None)
    if marker is None:
        raise SystemExit("Could not find NAMESPACE_MODULES insertion point in modules/middleware.py")
    text = text.replace(marker, marker + '\n    "planner": "planner",', 1)
    write(rel, text)
    print("Updated: module middleware planner gate")
else:
    print("No change needed: planner middleware gate already present")

# Enable registry seed and Standard package. Keep budgeting dependency from v10.4.
rel = "modules/management/commands/seed_modules.py"
text = read(rel)
original = text
new_spec = 'dict(key="planner", name="Wedding Planner", description="Planner tasks, checklist, appointments, reminders, notes and wedding-day run sheet.", system_enabled=True, visible_to_weddings=True, sort_order=250, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "WEDDING_PLANNER"]),'
if 'key="planner"' not in text:
    raise SystemExit("Planner registry seed entry not found. Install v10.4 Module Registry first.")
text = re.sub(r'dict\(key="planner"[^\n]+\),', new_spec, text, count=1)
# Ensure planner -> budgeting dependency exists.
if '"planner": ["budgeting"]' not in text:
    dep_marker = 'DEPENDENCIES = {'
    if dep_marker not in text:
        raise SystemExit("DEPENDENCIES registry not found in seed_modules.py")
    text = text.replace(dep_marker, dep_marker + '\n    "planner": ["budgeting"],', 1)
# Add planner to the package key set regardless of current order.
m = re.search(r'current_keys\s*=\s*\{([^}]*)\}', text, re.S)
if not m:
    raise SystemExit("Could not find current_keys in seed_modules.py")
body = m.group(1)
if '"planner"' not in body:
    stripped = body.rstrip()
    sep = "" if stripped.rstrip().endswith(",") or not stripped.strip() else ","
    body2 = stripped + sep + ' "planner"'
    text = text[:m.start(1)] + body2 + text[m.end(1):]
if text != original:
    write(rel, text)
    print("Updated: seed_modules planner state/dependency/default package")
else:
    print("No change needed: seed_modules already v11.2-ready")

# Add navigation without replacing shared layout.
rel = "weddings/templates/dashboard/base.html"
text = read(rel)
if "planner:dashboard" not in text:
    nav = '''            {% if access.planner and 'planner' in enabled_modules %}\n            <a class="nav-item {% if request.resolver_match.namespace == 'planner' %}active{% endif %}" href="{% url 'planner:dashboard' %}">Planner</a>\n            {% endif %}\n'''
    anchors = [
        r'(^\s*<a[^\n]+budgeting:dashboard[^\n]+Budget</a>\s*$)',
        r'(^\s*<a[^\n]+transportation:settings[^\n]+Transportation</a>\s*$)',
        r'(^\s*<a[^\n]+staffing:list[^\n]+Staff[^<]*</a>\s*$)',
    ]
    match = None
    for pattern in anchors:
        match = re.search(pattern, text, re.M)
        if match:
            break
    if match:
        text = text[:match.end()] + "\n" + nav.rstrip("\n") + text[match.end():]
    else:
        marker = '<div class="sidebar-quote">'
        if marker not in text:
            raise SystemExit("Could not find a safe Planner navigation anchor in dashboard/base.html")
        text = text.replace(marker, nav + marker, 1)
    write(rel, text)
    print("Updated: dashboard Planner navigation")
else:
    print("No change needed: Planner navigation already present")

# Improve Staff & Access role descriptions without replacing the template.
rel = "staffing/templates/staffing/list.html"
text = read(rel)
original = text
if "item.role == 'WEDDING_PLANNER'" not in text and "item.role == 'WEDDING_MANAGER'" in text:
    text = text.replace(
        "{% if item.role == 'WEDDING_MANAGER' %}Wedding, guests, invitations, RSVP, gifts, check-in, staff",
        "{% if item.role == 'WEDDING_MANAGER' %}Wedding, guests, invitations, RSVP, gifts, check-in, staff\n                        {% elif item.role == 'WEDDING_PLANNER' %}Planner workspace, tasks, appointments, notes and run sheet",
        1,
    )
if "<b>Wedding Planner</b>" not in text:
    marker = '<article><b>Wedding Manager</b><span>Can manage most wedding operations and staff.</span></article>'
    if marker in text:
        text = text.replace(marker, marker + '\n    <article><b>Wedding Planner</b><span>Planning workspace only; no ownership or invitation-setting authority by default.</span></article>', 1)
if text != original:
    write(rel, text)
    print("Updated: Staff & Access Planner role guide")
else:
    print("No change needed: Staff role guide already Planner-ready")

print(f"Backup created outside project: {BACKUP_ROOT}")
