import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.urls import resolve, reverse

match = resolve("/dashboard/planner/")
if match.namespace != "planner" or match.url_name != "dashboard":
    raise SystemExit(f"Unexpected planner resolver result: namespace={match.namespace!r}, name={match.url_name!r}")
url = reverse("planner:dashboard")
if url != "/dashboard/planner/":
    raise SystemExit(f"Unexpected planner reverse URL: {url}")
print("Planner route resolve/reverse: OK ->", url)
