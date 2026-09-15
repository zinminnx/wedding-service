from django.core.management.base import BaseCommand

from modules.models import FeatureModule, ServicePackage, WeddingModuleProfile
from weddings.models import Wedding


MODULES = [
    # Core
    dict(key="accounts", name="Accounts", description="Authentication and user accounts.", module_type="CORE", system_enabled=True, visible_to_weddings=False, sort_order=10),
    dict(key="weddings", name="Weddings", description="Wedding workspaces and settings.", module_type="CORE", system_enabled=True, visible_to_weddings=False, sort_order=20),
    dict(key="guests", name="Guests", description="Guest and guest-group management.", module_type="CORE", system_enabled=True, visible_to_weddings=True, sort_order=30),
    dict(key="invitations", name="Invitations", description="Personal invitations and secure invitation access.", module_type="CORE", system_enabled=True, visible_to_weddings=True, sort_order=40),

    # Implemented optional modules
    dict(key="staffing", name="Staff & Access", description="Wedding staff assignments and permissions.", system_enabled=True, visible_to_weddings=True, sort_order=100, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER"]),
    dict(key="rsvp", name="RSVP", description="Guest attendance responses and party counts.", system_enabled=True, visible_to_weddings=True, sort_order=110, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "RECEPTION_STAFF", "VIEWER"]),
    dict(key="gifts", name="Gifts & Payments", description="Optional wedding gifts and payment declarations.", system_enabled=True, visible_to_weddings=True, sort_order=120, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER"]),
    dict(key="checkins", name="Reception Check-in", description="Entrance QR and reception check-in operations.", system_enabled=True, visible_to_weddings=True, sort_order=130, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "RECEPTION_STAFF"]),
    dict(key="return_gifts", name="Return Gifts", description="Return-gift rules, inventory and issue history.", system_enabled=True, visible_to_weddings=True, sort_order=140, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "RECEPTION_STAFF"]),
    dict(key="photos", name="Guest Photos", description="Guest uploads, moderation and live slideshow.", system_enabled=True, visible_to_weddings=True, sort_order=150, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "PHOTO_STAFF"]),

    # Planned modules: registered now, disabled until their ZIP is installed.
    dict(key="printing", name="Printing", description="Cloud print queue for approved wedding photos; local printer agent arrives in v12.3.", system_enabled=True, visible_to_weddings=True, sort_order=200, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "PRINT_STAFF"]),
    dict(key="invitation_themes", name="Invitation Themes", description="Dynamic invitation themes and Design Studio.", system_enabled=True, visible_to_weddings=True, sort_order=210, allowed_roles=["WEDDING_OWNER"]),
    dict(key="dashboard_themes", name="Dashboard Themes", description="Per-user dashboard visual themes and layout density.", system_enabled=True, visible_to_weddings=False, sort_order=220),
    dict(key="transportation", name="Transportation", description="Guest travel guidance, maps and Bus Project provider integration.", system_enabled=True, visible_to_weddings=True, sort_order=230, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER"]),
    dict(key="budgeting", name="Budgeting", description="Couple budget, estimates, committed costs, payments and financial summary.", system_enabled=True, visible_to_weddings=True, sort_order=240, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "WEDDING_PLANNER"]),
    dict(key="planner", name="Wedding Planner", description="Planner tasks, checklist, appointments, reminders, notes and wedding-day run sheet.", system_enabled=True, visible_to_weddings=True, sort_order=250, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "WEDDING_PLANNER"]),
    dict(key="vendors", name="Vendors & Quotes", description="Wedding vendors, planner quotations, Owner approval and approved-cost budget integration.", system_enabled=True, visible_to_weddings=True, sort_order=255, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER", "WEDDING_PLANNER"]),
    dict(key="surveys", name="Surveys", description="Guest surveys and structured responses.", system_enabled=False, visible_to_weddings=False, sort_order=260),
    dict(key="onedrive", name="OneDrive Storage", description="Microsoft Graph storage foundation for media, documents and archive workflows.", system_enabled=True, visible_to_weddings=True, sort_order=270, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER"]),
    dict(key="archive_restore", name="Archive & Restore", description="Verified wedding export, retention lifecycle and safe non-destructive restore.", system_enabled=True, visible_to_weddings=True, sort_order=280, allowed_roles=["WEDDING_OWNER"]),
    dict(key="notifications", name="Notifications", description="Wedding and operational notifications.", system_enabled=False, visible_to_weddings=False, sort_order=290),
    dict(key="analytics", name="Audit & Analytics", description="Wedding operational analytics and owner audit trail.", system_enabled=True, visible_to_weddings=True, sort_order=300, allowed_roles=["WEDDING_OWNER", "WEDDING_MANAGER"]),
]

DEPENDENCIES = {
    "vendors": ["planner", "budgeting"],
    "return_gifts": ["checkins", "gifts"],
    "printing": ["photos"],
    "invitation_themes": ["invitations"],
    "transportation": ["invitations"],
    "planner": ["budgeting"],
    "archive_restore": ["onedrive"],
}


class Command(BaseCommand):
    help = "Create/update EverAfter module registry and the backward-compatible default package."

    def handle(self, *args, **options):
        registry = {}
        for spec in MODULES:
            data = dict(spec)
            key = data.pop("key")
            allowed_roles = data.pop("allowed_roles", [])
            data.setdefault("module_type", "OPTIONAL")
            data.setdefault("version", "1.0")
            data["allowed_roles"] = allowed_roles
            module, _ = FeatureModule.objects.update_or_create(key=key, defaults=data)
            registry[key] = module

        for module in registry.values():
            module.dependencies.clear()
        for key, dependency_keys in DEPENDENCIES.items():
            registry[key].dependencies.add(*(registry[item] for item in dependency_keys))

        package, _ = ServicePackage.objects.get_or_create(
            slug="standard",
            defaults={
                "name": "Standard",
                "description": "Backward-compatible default package for current weddings.",
                "is_active": True,
                "is_default": True,
            },
        )
        if not package.is_default or not package.is_active:
            package.is_default = True
            package.is_active = True
            package.save(update_fields=["is_default", "is_active", "updated_at"])

        current_keys = {"accounts", "weddings", "guests", "invitations", "staffing", "rsvp", "gifts", "checkins", "return_gifts", "photos", "invitation_themes", "transportation", "budgeting", "planner", "vendors", "onedrive", "printing", "archive_restore", "analytics"}
        package.modules.set([registry[key] for key in current_keys])

        created_profiles = 0
        for wedding in Wedding.objects.all().only("pk"):
            _, created = WeddingModuleProfile.objects.get_or_create(
                wedding=wedding,
                defaults={"package": package},
            )
            created_profiles += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"Module registry ready: {len(registry)} modules, default package '{package.name}', "
            f"{created_profiles} wedding profile(s) created."
        ))
