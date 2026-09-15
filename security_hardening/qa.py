from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core import checks
from django.db import connection
from django.db.models import F, Q
from django.db.migrations.executor import MigrationExecutor
from django.urls import NoReverseMatch, reverse


@dataclass
class QAItem:
    code: str
    level: str
    message: str
    detail: str = ""


class QAReport:
    def __init__(self):
        self.items: list[QAItem] = []

    def add(self, code: str, level: str, message: str, detail: str = "") -> None:
        self.items.append(QAItem(code=code, level=level, message=message, detail=detail))

    def passed(self, code: str, message: str, detail: str = "") -> None:
        self.add(code, "PASS", message, detail)

    def warn(self, code: str, message: str, detail: str = "") -> None:
        self.add(code, "WARN", message, detail)

    def fail(self, code: str, message: str, detail: str = "") -> None:
        self.add(code, "FAIL", message, detail)

    @property
    def counts(self) -> dict[str, int]:
        result = {"PASS": 0, "WARN": 0, "FAIL": 0}
        for item in self.items:
            result[item.level] = result.get(item.level, 0) + 1
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "everafter_version": "14.1",
            "production_mode": bool(getattr(settings, "EVERAFTER_PRODUCTION", False)),
            "debug": bool(getattr(settings, "DEBUG", False)),
            "counts": self.counts,
            "items": [asdict(item) for item in self.items],
        }

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        if not target.is_absolute():
            target = Path(settings.BASE_DIR) / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return target


CORE_APPS = (
    "accounts",
    "weddings",
    "guests",
    "invitations",
    "staffing",
    "modules",
    "security_hardening",
)

MILESTONE_APPS = (
    "rsvp",
    "payment_providers",
    "gifts",
    "checkins",
    "photos",
    "invitation_themes",
    "event_tools",
    "transportation",
    "budgeting",
    "planner",
    "vendors",
    "financial_docs",
    "integrations",
    "printing",
    "archive_restore",
    "dashboard_themes",
    "audit_analytics",
)

ROUTES = {
    "weddings": ("weddings:dashboard",),
    "guests": ("guests:list",),
    "invitations": ("invitations:list",),
    "rsvp": ("rsvp:list",),
    "gifts": ("gifts:dashboard",),
    "checkins": ("checkins:dashboard",),
    "photos": ("photos:dashboard",),
    "modules": ("modules:wedding_modules",),
    "invitation_themes": ("invitation_themes:studio",),
    "event_tools": ("event_tools:settings",),
    "transportation": ("transportation:settings",),
    "budgeting": ("budgeting:dashboard",),
    "planner": ("planner:dashboard",),
    "vendors": ("vendors:dashboard",),
    "financial_docs": ("financial_docs:dashboard",),
    "integrations": ("integrations:storage_dashboard",),
    "printing": ("printing:dashboard",),
    "archive_restore": ("archive_restore:dashboard",),
    "dashboard_themes": ("dashboard_themes:gallery",),
    "audit_analytics": ("audit_analytics:dashboard", "audit_analytics:audit"),
}


def _is_installed(app_label: str) -> bool:
    try:
        apps.get_app_config(app_label)
        return True
    except LookupError:
        return False


def _project_app_exists(app_label: str) -> bool:
    return (Path(settings.BASE_DIR) / app_label / "apps.py").exists()


def _model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def check_django(report: QAReport) -> None:
    messages = checks.run_checks()
    errors = [item for item in messages if item.level >= checks.ERROR]
    warnings = [item for item in messages if checks.WARNING <= item.level < checks.ERROR]
    if errors:
        report.fail("django.check", f"Django system check has {len(errors)} error(s).", "; ".join(str(x) for x in errors[:5]))
    else:
        report.passed("django.check", "Django system check has no errors.")
    if warnings:
        report.warn("django.warnings", f"Django system check has {len(warnings)} warning(s).", "; ".join(str(x) for x in warnings[:5]))


def check_database(report: QAReport) -> None:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            value = cursor.fetchone()[0]
        if value == 1:
            report.passed("database.connection", "Database connection is healthy.")
        else:
            report.fail("database.connection", "Database health query returned an unexpected result.")
    except Exception as exc:
        report.fail("database.connection", "Database connection failed.", str(exc))
        return

    try:
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        pending = executor.migration_plan(targets)
        if pending:
            names = [f"{migration.app_label}.{migration.name}" for migration, _backwards in pending[:12]]
            report.fail("database.migrations", f"{len(pending)} migration(s) are pending.", ", ".join(names))
        else:
            report.passed("database.migrations", "No pending migrations.")
    except Exception as exc:
        report.fail("database.migrations", "Migration graph could not be validated.", str(exc))


def check_apps(report: QAReport) -> None:
    missing_core = [label for label in CORE_APPS if not _is_installed(label)]
    if missing_core:
        report.fail("apps.core", "Required core apps are missing from INSTALLED_APPS.", ", ".join(missing_core))
    else:
        report.passed("apps.core", "Core EverVow apps are installed.")

    missing_installed = []
    absent = []
    for label in MILESTONE_APPS:
        exists = _project_app_exists(label)
        installed = _is_installed(label)
        if exists and not installed:
            missing_installed.append(label)
        elif not exists:
            absent.append(label)
    if missing_installed:
        report.fail("apps.registration", "Milestone app directories exist but are not registered.", ", ".join(missing_installed))
    else:
        report.passed("apps.registration", "Installed milestone apps are registered.")
    if absent:
        report.warn("apps.milestones", "Some roadmap app directories are not present in this checkout.", ", ".join(absent))
    else:
        report.passed("apps.milestones", "All roadmap app directories through v14.0 are present.")


def check_routes(report: QAReport) -> None:
    failures = []
    checked = 0
    for app_label, names in ROUTES.items():
        if not _is_installed(app_label):
            continue
        for name in names:
            try:
                reverse(name)
                checked += 1
            except NoReverseMatch as exc:
                failures.append(f"{name}: {exc}")
    try:
        reverse("security_hardening:live")
        reverse("security_hardening:ready")
        checked += 2
    except NoReverseMatch as exc:
        failures.append(f"health routes: {exc}")
    if failures:
        report.fail("urls.reverse", f"{len(failures)} critical route(s) could not be reversed.", "; ".join(failures[:8]))
    else:
        report.passed("urls.reverse", f"{checked} critical route(s) reversed successfully.")


def _count_mismatch(qs, label: str, report: QAReport, code: str) -> None:
    try:
        count = qs.count()
    except Exception as exc:
        report.warn(code, f"Could not evaluate {label} integrity check.", str(exc))
        return
    if count:
        report.fail(code, f"{count} {label} cross-wedding integrity problem(s) found.")
    else:
        report.passed(code, f"No {label} cross-wedding integrity problems found.")


def check_tenant_integrity(report: QAReport) -> None:
    Guest = _model("guests", "Guest")
    if Guest:
        _count_mismatch(
            Guest.objects.filter(group__isnull=False).exclude(wedding_id=F("group__wedding_id")),
            "Guest/Group",
            report,
            "tenant.guests",
        )

    Invitation = _model("invitations", "Invitation")
    if Invitation:
        _count_mismatch(
            Invitation.objects.exclude(wedding_id=F("guest__wedding_id")),
            "Invitation/Guest",
            report,
            "tenant.invitations",
        )
        blank_tokens = Invitation.objects.filter(Q(token="") | Q(qr_token="")).count()
        if blank_tokens:
            report.fail("tokens.invitation", f"{blank_tokens} invitation(s) have a blank secure token or QR token.")
        else:
            report.passed("tokens.invitation", "Invitation token and QR token fields are populated.")

    RSVP = _model("rsvp", "RSVP")
    if RSVP:
        _count_mismatch(
            RSVP.objects.exclude(wedding_id=F("guest__wedding_id"))
            | RSVP.objects.exclude(wedding_id=F("invitation__wedding_id"))
            | RSVP.objects.exclude(guest_id=F("invitation__guest_id")),
            "RSVP relation",
            report,
            "tenant.rsvp",
        )

    CheckIn = _model("checkins", "CheckIn")
    if CheckIn:
        _count_mismatch(
            CheckIn.objects.exclude(wedding_id=F("guest__wedding_id"))
            | CheckIn.objects.exclude(wedding_id=F("invitation__wedding_id"))
            | CheckIn.objects.exclude(guest_id=F("invitation__guest_id")),
            "Check-in relation",
            report,
            "tenant.checkin",
        )
        invalid_overrides = CheckIn.objects.filter(
            checked_in_count__gt=F("guest__allowed_party_size"),
            limit_overridden=False,
        ).count()
        if invalid_overrides:
            report.fail("checkin.override", f"{invalid_overrides} check-in record(s) exceed party size without an override.")
        else:
            report.passed("checkin.override", "No unapproved party-size overages found.")

    Photo = _model("photos", "WeddingPhoto")
    if Photo:
        bad = Photo.objects.filter(guest__isnull=False).exclude(wedding_id=F("guest__wedding_id"))
        if hasattr(Photo, "invitation"):
            pass
        bad_count = bad.count()
        invitation_bad = Photo.objects.filter(invitation__isnull=False).exclude(wedding_id=F("invitation__wedding_id")).count()
        if bad_count or invitation_bad:
            report.fail("tenant.photos", f"{bad_count + invitation_bad} Photo guest/invitation wedding mismatch(es) found.")
        else:
            report.passed("tenant.photos", "Photo relations remain wedding-scoped.")
        if any(field.name == "storage_object" for field in Photo._meta.get_fields()):
            storage_bad = Photo.objects.filter(storage_object__isnull=False).exclude(wedding_id=F("storage_object__wedding_id")).count()
            if storage_bad:
                report.fail("tenant.photo_storage", f"{storage_bad} photo storage object(s) belong to another wedding.")
            else:
                report.passed("tenant.photo_storage", "Photo storage objects remain wedding-scoped.")

    PrintJob = _model("printing", "PrintJob")
    if PrintJob:
        photo_bad = PrintJob.objects.filter(photo__isnull=False).exclude(wedding_id=F("photo__wedding_id")).count()
        unapproved = PrintJob.objects.filter(
            photo__isnull=False,
            status__in=["QUEUED", "CLAIMED", "PRINTING"],
        ).exclude(photo__status="APPROVED").count()
        if photo_bad:
            report.fail("tenant.printing", f"{photo_bad} print job(s) reference a photo from another wedding.")
        else:
            report.passed("tenant.printing", "Print jobs remain wedding-scoped.")
        if unapproved:
            report.fail("printing.approval", f"{unapproved} active print job(s) reference a non-approved photo.")
        else:
            report.passed("printing.approval", "Active print jobs only reference approved photos.")

    BudgetItem = _model("budgeting", "BudgetItem")
    if BudgetItem and hasattr(BudgetItem, "Visibility"):
        planner_private = BudgetItem.objects.filter(source="PLANNER").exclude(visibility="SHARED").count()
        if planner_private:
            report.fail("finance.visibility", f"{planner_private} Planner Budget item(s) are not SHARED as required.")
        else:
            report.passed("finance.visibility", "Planner Budget items satisfy shared-visibility rules.")

    FinancialDocument = _model("financial_docs", "FinancialDocument")
    if FinancialDocument:
        budget_bad = FinancialDocument.objects.filter(budget_item__isnull=False).exclude(wedding_id=F("budget_item__wedding_id")).count()
        vendor_bad = FinancialDocument.objects.filter(vendor_quote__isnull=False).exclude(wedding_id=F("vendor_quote__wedding_id")).count()
        if budget_bad or vendor_bad:
            report.fail("tenant.financial_docs", f"{budget_bad + vendor_bad} financial document relation mismatch(es) found.")
        else:
            report.passed("tenant.financial_docs", "Financial documents remain wedding-scoped.")


def check_storage_metadata(report: QAReport) -> None:
    StoredObject = _model("integrations", "StoredObject")
    if not StoredObject:
        return
    remote_without_id = StoredObject.objects.filter(backend="ONEDRIVE", status="AVAILABLE", remote_item_id="").count()
    if remote_without_id:
        report.fail("storage.remote_id", f"{remote_without_id} available OneDrive object(s) have no remote item id.")
    else:
        report.passed("storage.remote_id", "Available OneDrive objects have remote item ids.")
    failed = StoredObject.objects.filter(status="FAILED").count()
    if failed:
        report.warn("storage.failed", f"{failed} storage object(s) are in FAILED state; review before production.")
    else:
        report.passed("storage.failed", "No storage objects are currently marked FAILED.")


def check_archive_state(report: QAReport) -> None:
    ArchiveSnapshot = _model("archive_restore", "ArchiveSnapshot")
    if not ArchiveSnapshot:
        return
    ready_unverified = ArchiveSnapshot.objects.filter(status="READY", verified_at__isnull=True).count()
    if ready_unverified:
        report.fail("archive.verify", f"{ready_unverified} READY archive snapshot(s) are not marked verified.")
    else:
        report.passed("archive.verify", "READY archive snapshots are verified.")
    bad_hash = ArchiveSnapshot.objects.filter(status__in=["READY", "RESTORED"]).exclude(sha256__regex=r"^[0-9a-fA-F]{64}$").count()
    if bad_hash:
        report.warn("archive.hash", f"{bad_hash} ready/restored archive(s) do not have a 64-character SHA-256 value.")
    else:
        report.passed("archive.hash", "Ready/restored archives have SHA-256 metadata.")


def check_security_config(report: QAReport) -> None:
    production = bool(getattr(settings, "EVERAFTER_PRODUCTION", False))
    if not production:
        report.warn("security.mode", "Local development mode is active; production-only HTTPS checks are not expected to pass yet.")
        return

    failures = []
    if settings.DEBUG:
        failures.append("DEBUG=True")
    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        failures.append("SESSION_COOKIE_SECURE=False")
    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        failures.append("CSRF_COOKIE_SECURE=False")
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        failures.append("SECURE_SSL_REDIRECT=False")
    if int(getattr(settings, "SECURE_HSTS_SECONDS", 0) or 0) < 3600:
        failures.append("SECURE_HSTS_SECONDS<3600")
    if failures:
        report.fail("security.production", "Production security settings are incomplete.", ", ".join(failures))
    else:
        report.passed("security.production", "Production HTTPS/cookie baseline is enabled.")


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
        )
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)


def check_git(report: QAReport) -> None:
    root = Path(settings.BASE_DIR)
    if not (root / ".git").exists():
        report.warn("git.repo", "This checkout has no .git directory; release cleanliness was not checked.")
        return

    code, tracked_env = _git(root, "ls-files", ".env", "local_print_agent/agent.env")
    if code == 0 and tracked_env:
        report.fail("git.secrets", "A secret-bearing runtime environment file is tracked by Git.", tracked_env)
    elif code == 0:
        report.passed("git.secrets", "Known runtime secret files are not tracked by Git.")
    else:
        report.warn("git.secrets", "Could not inspect tracked secret files.", tracked_env)

    code, status = _git(root, "status", "--porcelain")
    if code == 0 and status:
        lines = status.splitlines()
        report.warn("git.dirty", f"Working tree has {len(lines)} uncommitted path(s).", "; ".join(lines[:10]))
    elif code == 0:
        report.passed("git.dirty", "Git working tree is clean.")
    else:
        report.warn("git.dirty", "Could not inspect Git working tree.", status)


def run_full_qa(*, quick: bool = False, skip_git: bool = False) -> QAReport:
    report = QAReport()
    check_django(report)
    check_database(report)
    check_apps(report)
    check_routes(report)
    check_security_config(report)
    if not quick:
        check_tenant_integrity(report)
        check_storage_metadata(report)
        check_archive_state(report)
    if not skip_git:
        check_git(report)
    return report
