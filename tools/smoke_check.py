from pathlib import Path
import os
import sys

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.apps import apps
from django.urls import resolve, reverse
from planner.models import PlannerTask, PlannerAppointment, PlannerNote, RunSheetItem

assert apps.is_installed("planner")
assert resolve("/dashboard/planner/").namespace == "planner"
assert reverse("planner:dashboard") == "/dashboard/planner/"
assert PlannerTask._meta.get_field("wedding")
assert PlannerAppointment._meta.get_field("wedding")
assert PlannerNote._meta.get_field("wedding")
assert RunSheetItem._meta.get_field("wedding")
print("Planner app, route and core models: OK")
