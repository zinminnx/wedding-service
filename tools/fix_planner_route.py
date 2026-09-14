from pathlib import Path
import datetime
import re
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
BACKUP_ROOT = ROOT.parent / "_everafter_patch_backups" / ("v11_2_1_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def require(rel):
    path = ROOT / rel
    if not path.exists():
        raise SystemExit(f"Required file not found: {rel}. Install v11.2 Planner Module first.")
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
    path.write_text(text, encoding="utf-8")


require("manage.py")
require("planner/apps.py")
require("planner/urls.py")
require("planner/views.py")

# Ensure planner is installed without disturbing app ordering.
rel = "config/settings.py"
text = read(rel)
if re.search(r'^\s*["\']planner["\'],?\s*$', text, re.M) is None:
    anchors = ['    "budgeting",', '    "transportation",', '    "event_tools",']
    marker = next((a for a in anchors if a in text), None)
    if marker is None:
        raise SystemExit("Could not find a safe INSTALLED_APPS anchor in config/settings.py")
    text = text.replace(marker, marker + '\n    "planner",', 1)
    write(rel, text)
    print("Fixed: planner added to INSTALLED_APPS")
else:
    print("OK: planner already in INSTALLED_APPS")

# The 404 screenshot shows planner.urls was not included in the project URLConf.
rel = "config/urls.py"
text = read(rel)
if 'include("planner.urls")' not in text and "include('planner.urls')" not in text:
    marker = "urlpatterns = ["
    if marker not in text:
        raise SystemExit("Could not find urlpatterns in config/urls.py")
    text = text.replace(marker, marker + '\n    path("", include("planner.urls")),', 1)
    write(rel, text)
    print("Fixed: planner URLs added to config/urls.py")
else:
    print("OK: planner URLs already included")

print(f"Backup created outside project: {BACKUP_ROOT}")
