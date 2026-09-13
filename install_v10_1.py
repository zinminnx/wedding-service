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
    backup_path = path.with_suffix(path.suffix + ".v10_1.bak")
    if path.exists() and not backup_path.exists():
        shutil.copy2(path, backup_path)
        print(f"Backup: {backup_path}")


def copy_file(relative: str):
    source = PAYLOAD / relative
    target = ROOT / relative
    require(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup(target)
    shutil.copy2(source, target)
    print(f"Updated: {relative}")


# Guard against running from the wrong directory.
require(ROOT / "manage.py")
require(ROOT / "weddings" / "forms.py")
require(ROOT / "weddings" / "static" / "weddings" / "css" / "dashboard.css")

copy_file("weddings/templates/dashboard/wedding_overview.html")
copy_file("weddings/static/weddings/js/wedding-editor.js")

# Append isolated wizard styles instead of replacing the shared dashboard stylesheet.
css_path = ROOT / "weddings" / "static" / "weddings" / "css" / "dashboard.css"
css = css_path.read_text(encoding="utf-8")
styles = (PATCH_ROOT / "wizard_styles.css").read_text(encoding="utf-8")
marker = "/* EverAfter v10.1 - Four-step Wedding Wizard */"
if marker not in css:
    backup(css_path)
    css_path.write_text(css.rstrip() + "\n\n" + styles.rstrip() + "\n", encoding="utf-8")
    print("Updated: weddings/static/weddings/css/dashboard.css (wizard styles appended)")
else:
    print("No change needed: wizard styles already installed")

# Bump the dashboard stylesheet cache key without disturbing v7/v10 sidebar integrations.
base_path = ROOT / "weddings" / "templates" / "dashboard" / "base.html"
if base_path.exists():
    base = base_path.read_text(encoding="utf-8")
    updated = re.sub(r"dashboard\.css' %\}\?v=[^\"']+", "dashboard.css' %}?v=10.1", base, count=1)
    if updated != base:
        backup(base_path)
        base_path.write_text(updated, encoding="utf-8")
        print("Updated: dashboard.css cache key")

print("EverAfter v10.1 wedding wizard installed successfully.")
