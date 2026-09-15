from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import ProfileImageAsset
from integrations.graph import GraphAPIError, OneDriveGraphClient, get_graph_config
from integrations.models import StoredObject, WeddingStorageSettings


class Command(BaseCommand):
    help = "Rename the legacy OneDrive root folder from EverAfter to EverVow and update stored metadata."

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true", help="Apply the remote folder rename and DB metadata updates.")
        parser.add_argument("--old", default="EverAfter")
        parser.add_argument("--new", default="EverVow")

    @staticmethod
    def _replace_prefix(value, old, new):
        value = value or ""
        if value == old:
            return new
        if value.startswith(old + "/"):
            return new + value[len(old):]
        return value

    @staticmethod
    def _replace_url(value, old, new):
        value = value or ""
        return value.replace(f"/{old}/", f"/{new}/")

    def handle(self, *args, **options):
        old = (options["old"] or "EverAfter").strip(" /\\")
        new = (options["new"] or "EverVow").strip(" /\\")
        execute = bool(options["execute"])
        if not old or not new or old == new:
            raise CommandError("Old and new root folder names must be different non-empty values.")

        config = get_graph_config()
        client = OneDriveGraphClient(config)
        drive = client.health_check()
        self.stdout.write(f"Drive: {drive.get('name', 'OneDrive')} ({config.drive_id})")

        old_item = None
        new_item = None
        try:
            old_item = client.get_item_by_path(old)
        except GraphAPIError as exc:
            if "HTTP 404" not in str(exc):
                raise
        try:
            new_item = client.get_item_by_path(new)
        except GraphAPIError as exc:
            if "HTTP 404" not in str(exc):
                raise

        stored_qs = StoredObject.objects.filter(relative_path__startswith=old + "/")
        profile_qs = ProfileImageAsset.objects.filter(remote_path__startswith=old + "/")
        wedding_qs = WeddingStorageSettings.objects.filter(root_folder__startswith=old)

        self.stdout.write(f"Legacy remote folder: {'found' if old_item else 'not found'}")
        self.stdout.write(f"EverVow remote folder: {'already exists' if new_item else 'not found'}")
        self.stdout.write(f"StoredObject path rows to update: {stored_qs.count()}")
        self.stdout.write(f"ProfileImageAsset path rows to update: {profile_qs.count()}")
        self.stdout.write(f"WeddingStorageSettings rows to update: {wedding_qs.count()}")

        if old_item and new_item and old_item.get("id") != new_item.get("id"):
            raise CommandError(
                f"Both {old!r} and {new!r} folders exist. Automatic merge is intentionally refused. "
                "Move/delete the old folder manually, then run this command again."
            )

        if not execute:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --execute to apply changes."))
            return

        if old_item and not new_item:
            item_id = old_item.get("id")
            if not item_id:
                raise CommandError("Legacy OneDrive folder lookup returned no item ID.")
            renamed = client.rename_item(item_id, new)
            self.stdout.write(self.style.SUCCESS(f"Renamed OneDrive folder {old} -> {renamed.get('name', new)}"))

        with transaction.atomic():
            for record in stored_qs.select_for_update():
                record.relative_path = self._replace_prefix(record.relative_path, old, new)
                record.remote_web_url = self._replace_url(record.remote_web_url, old, new)
                record.save(update_fields=["relative_path", "remote_web_url", "updated_at"])
            for asset in profile_qs.select_for_update():
                asset.remote_path = self._replace_prefix(asset.remote_path, old, new)
                asset.remote_web_url = self._replace_url(asset.remote_web_url, old, new)
                asset.save(update_fields=["remote_path", "remote_web_url", "updated_at"])
            for settings_obj in wedding_qs.select_for_update():
                settings_obj.root_folder = self._replace_prefix(settings_obj.root_folder, old, new)
                settings_obj.save(update_fields=["root_folder", "updated_at"])

        self.stdout.write(self.style.SUCCESS("EverVow OneDrive root rebrand completed."))
