from pathlib import Path


def read(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Required file not found: {path}. Run this patch from the project root.")
    return p, p.read_text(encoding="utf-8")


def write_if_changed(path, original, updated):
    if updated == original:
        print(f"No change needed: {path}")
        return
    Path(path).write_text(updated, encoding="utf-8")
    print(f"Updated: {path}")


# 1) Install app and ensure local MEDIA settings exist.
settings_path, text = read("config/settings.py")
original = text
if '"photos"' not in text and "'photos'" not in text:
    marker = "INSTALLED_APPS = ["
    if marker not in text:
        raise SystemExit("Could not find INSTALLED_APPS in config/settings.py")
    text = text.replace(marker, marker + '\n    "photos",', 1)

if "MEDIA_URL" not in text:
    text += '\n\n# Uploaded media - local development. OneDrive storage is added in a later milestone.\nMEDIA_URL = "/media/"\nMEDIA_ROOT = BASE_DIR / "media"\n'
write_if_changed(settings_path, original, text)


# 2) Register photo URLs without replacing the user's current route file.
urls_path, text = read("config/urls.py")
original = text
route = '    path("", include("photos.urls")),\n'
if 'include("photos.urls")' not in text and "include('photos.urls')" not in text:
    marker = "urlpatterns = [\n"
    if marker not in text:
        raise SystemExit("Could not find urlpatterns in config/urls.py")
    text = text.replace(marker, marker + route, 1)
write_if_changed(urls_path, original, text)


# 3) Turn the reserved Photos sidebar item from v7 into a real destination.
base_path, text = read("weddings/templates/dashboard/base.html")
original = text
old = '{% if access.photo %}<a class="nav-item disabled" href="#">Photos</a>{% endif %}'
new = '{% if access.photo %}<a class="nav-item {% if request.resolver_match.namespace == \'photos\' %}active{% endif %}" href="{% url \'photos:dashboard\' %}">Photos</a>{% endif %}'
if old in text:
    text = text.replace(old, new, 1)
elif "photos:dashboard" not in text:
    print("WARNING: Could not find the reserved Photos sidebar line. Photo dashboard still works at /dashboard/photos/.")
write_if_changed(base_path, original, text)


# 4) Add a guest-facing photo entry point to the existing luxury invitation without replacing it.
detail_path, text = read("invitations/templates/invitations/detail.html")
original = text
if "photos:guest_upload" not in text:
    marker = '<section class="section gift-card" id="gift">'
    block = '''<section class="section" id="photos">
            <p class="script">Share a Moment</p>
            <h2>Captured something beautiful?</h2>
            <p>Share photos from the celebration with the couple. New uploads may be reviewed before they appear on the live wedding slideshow.</p>
            <a class="primary-action" href="{% url 'photos:guest_upload' invitation.token %}" style="text-decoration:none;display:flex;align-items:center;justify-content:center;">Share Wedding Photos</a>
        </section>

        '''
    if marker in text:
        text = text.replace(marker, block + marker, 1)
    else:
        print("WARNING: Could not find the gift section in invitation detail. Guest upload still works at /i/<token>/photos/.")
write_if_changed(detail_path, original, text)

print("EverAfter v10 integration complete.")
