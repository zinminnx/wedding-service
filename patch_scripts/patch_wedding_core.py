from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()


def read(rel):
    return (root / rel).read_text(encoding="utf-8-sig")


def write(rel, text):
    (root / rel).write_text(text, encoding="utf-8", newline="")


# 1) Wedding model: keep wedding_location as the backwards-compatible venue name.
rel = "weddings/models.py"
text = read(rel)
if "venue_full_address" not in text:
    marker = "    wedding_location = models.CharField(max_length=255, blank=True)\n\n    google_maps_url = models.URLField(max_length=1000, blank=True)"
    replacement = """    # Venue master data. wedding_location is retained as the canonical venue name\n    # for backwards compatibility with earlier EverAfter releases.\n    wedding_location = models.CharField(max_length=255, blank=True)\n    venue_full_address = models.CharField(max_length=500, blank=True)\n    venue_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)\n    venue_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)\n    venue_landmark = models.CharField(max_length=255, blank=True)\n    venue_location_note = models.TextField(blank=True)\n\n    google_maps_url = models.URLField(max_length=1000, blank=True)"""
    if marker not in text:
        raise SystemExit("Could not find the Wedding venue model marker. Stop; no partial model patch applied.")
    text = text.replace(marker, replacement, 1)
    write(rel, text)
    print("Patched: weddings/models.py")
else:
    print("No change needed: Wedding venue master fields already present")

# 2) Wedding form: expose the venue master fields only in Wedding Details.
rel = "weddings/forms.py"
text = read(rel)
if '"venue_full_address"' not in text:
    fields_marker = '            "wedding_location",\n            "google_maps_url",'
    fields_replacement = '''            "wedding_location",\n            "venue_full_address",\n            "venue_latitude",\n            "venue_longitude",\n            "venue_landmark",\n            "venue_location_note",\n            "google_maps_url",'''
    if fields_marker not in text:
        raise SystemExit("Could not find WeddingForm venue fields marker.")
    text = text.replace(fields_marker, fields_replacement, 1)

    widget_marker = '            "wedding_location": forms.TextInput(attrs={"placeholder": "e.g. Novotel Yangon Max, Yangon"}),\n            "google_maps_url": forms.URLInput(attrs={"placeholder": "https://maps.app.goo.gl/..."}),'
    widget_replacement = '''            "wedding_location": forms.TextInput(attrs={"placeholder": "e.g. Novotel Yangon Max"}),\n            "venue_full_address": forms.TextInput(attrs={"placeholder": "Full venue address"}),\n            "venue_latitude": forms.NumberInput(attrs={"step": "0.0000001", "min": -90, "max": 90, "placeholder": "16.8123000"}),\n            "venue_longitude": forms.NumberInput(attrs={"step": "0.0000001", "min": -180, "max": 180, "placeholder": "96.1399000"}),\n            "venue_landmark": forms.TextInput(attrs={"placeholder": "Nearby landmark (optional)"}),\n            "venue_location_note": forms.Textarea(attrs={"rows": 3, "placeholder": "Entrance, parking or arrival note (optional)"}),\n            "google_maps_url": forms.URLInput(attrs={"placeholder": "https://maps.app.goo.gl/..."}),'''
    if widget_marker not in text:
        raise SystemExit("Could not find WeddingForm venue widget marker.")
    text = text.replace(widget_marker, widget_replacement, 1)

    validation_marker = '        if wedding_date and expire_date and expire_date <= wedding_date:\n            self.add_error("expire_date", "Expire date must be after the wedding date.")\n\n        return cleaned'
    validation_replacement = '''        if wedding_date and expire_date and expire_date <= wedding_date:\n            self.add_error("expire_date", "Expire date must be after the wedding date.")\n\n        latitude = cleaned.get("venue_latitude")\n        longitude = cleaned.get("venue_longitude")\n        if (latitude is None) != (longitude is None):\n            self.add_error("venue_latitude", "Latitude and longitude should be provided together.")\n            self.add_error("venue_longitude", "Latitude and longitude should be provided together.")\n\n        return cleaned'''
    if validation_marker not in text:
        raise SystemExit("Could not find WeddingForm validation marker.")
    text = text.replace(validation_marker, validation_replacement, 1)
    write(rel, text)
    print("Patched: weddings/forms.py")
else:
    print("No change needed: WeddingForm venue master fields already present")

# 3) Wedding wizard: make Step 3 the only editor for venue master data.
rel = "weddings/templates/dashboard/wedding_overview.html"
text = read(rel)
if "venue_full_address.id_for_label" not in text:
    pattern = re.compile(r'\n\s*<div class="venue-card">.*?</div>\n\n\s*<div class="timezone-card">', re.S)
    replacement = r'''
                <div class="venue-card" id="venue-master-data">
                    <div class="venue-card-head">
                        <div><span class="venue-pin">⌖</span><div><strong>Wedding venue</strong><p>This is the single source of truth used by invitations, calendar, maps and future transportation features.</p></div></div>
                    </div>
                    <div class="premium-form-grid two-col venue-fields">
                        <div class="field-wrap">
                            <label for="{{ form.wedding_location.id_for_label }}">Venue Name</label>
                            {{ form.wedding_location }}
                            <small>Example: Novotel Yangon Max.</small>
                            {{ form.wedding_location.errors }}
                        </div>
                        <div class="field-wrap">
                            <label for="{{ form.google_maps_url.id_for_label }}">Google Maps URL</label>
                            {{ form.google_maps_url }}
                            <small>Google Maps → Share → Copy link.</small>
                            {{ form.google_maps_url.errors }}
                        </div>
                        <div class="field-wrap venue-full-span">
                            <label for="{{ form.venue_full_address.id_for_label }}">Full Address</label>
                            {{ form.venue_full_address }}
                            <small>Street, township/city and any address details guests may need.</small>
                            {{ form.venue_full_address.errors }}
                        </div>
                        <div class="field-wrap">
                            <label for="{{ form.venue_latitude.id_for_label }}">Latitude</label>
                            {{ form.venue_latitude }}
                            <small>Optional; use together with longitude for precise map routing.</small>
                            {{ form.venue_latitude.errors }}
                        </div>
                        <div class="field-wrap">
                            <label for="{{ form.venue_longitude.id_for_label }}">Longitude</label>
                            {{ form.venue_longitude }}
                            <small>Optional; use together with latitude.</small>
                            {{ form.venue_longitude.errors }}
                        </div>
                        <div class="field-wrap">
                            <label for="{{ form.venue_landmark.id_for_label }}">Landmark</label>
                            {{ form.venue_landmark }}
                            <small>Optional nearby landmark.</small>
                            {{ form.venue_landmark.errors }}
                        </div>
                        <div class="field-wrap">
                            <label for="{{ form.venue_location_note.id_for_label }}">Location Note</label>
                            {{ form.venue_location_note }}
                            <small>Entrance, parking, floor or arrival instructions.</small>
                            {{ form.venue_location_note.errors }}
                        </div>
                    </div>
                    <div class="venue-map-preview" id="venue-map-preview"{% if not wedding.google_maps_url %} hidden{% endif %}>
                        <span>Map link ready</span>
                        <a id="venue-map-link" href="{{ wedding.google_maps_url|default:'#' }}" target="_blank" rel="noopener noreferrer">Open Google Maps ↗</a>
                    </div>
                </div>

                <div class="timezone-card">'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit("Could not find the Wedding wizard venue-card block.")
    write(rel, text)
    print("Patched: wedding_overview.html")
else:
    print("No change needed: Wedding wizard venue master UI already present")

# 4) Wedding editor JS: support direct Edit Wedding Venue link via ?step=3.
rel = "weddings/static/weddings/js/wedding-editor.js"
text = read(rel)
if "requestedStep" not in text:
    marker = "    updatePreview();\n    setStep(stepContainingErrors() || 1);"
    replacement = '''    updatePreview();\n    const requestedStep = Number(new URLSearchParams(window.location.search).get('step'));\n    const initialStep = stepContainingErrors() || ([1, 2, 3, 4].includes(requestedStep) ? requestedStep : 1);\n    setStep(initialStep);'''
    if marker not in text:
        raise SystemExit("Could not find wedding-editor.js initialization marker.")
    text = text.replace(marker, replacement, 1)
    write(rel, text)
    print("Patched: wedding-editor.js")
else:
    print("No change needed: direct wizard step support already present")

# 5) Add a tiny layout helper without replacing shared dashboard CSS.
rel = "weddings/static/weddings/css/dashboard.css"
text = read(rel)
marker = "/* v10.8.1 venue master data */"
if marker not in text:
    text += "\n\n" + marker + "\n.venue-fields .venue-full-span{grid-column:1/-1}.venue-fields textarea{width:100%;box-sizing:border-box;resize:vertical}@media(max-width:700px){.venue-fields .venue-full-span{grid-column:auto}}\n"
    write(rel, text)
    print("Patched: dashboard.css (additive only)")
else:
    print("No change needed: venue master CSS already present")
