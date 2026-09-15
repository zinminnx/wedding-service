import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db import transaction
from django.db.models import FileField
from django.utils import timezone

from integrations.models import StoredObject
from integrations.storage import read_stored_object, store_bytes
from weddings.models import Wedding

from .models import ArchiveEvent, ArchiveSnapshot


ARCHIVE_FORMAT = "everafter-archive-v1"
DEFAULT_MAX_BYTES = 512 * 1024 * 1024


class ArchiveError(RuntimeError):
    pass


def _event(snapshot, action, actor=None, message=""):
    return ArchiveEvent.objects.create(
        snapshot=snapshot,
        wedding_public_id=snapshot.wedding_public_id,
        actor=actor,
        action=action,
        message=(message or "")[:500],
    )


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str).encode("utf-8")


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _safe_member(value):
    value = str(value or "item").replace("\\", "/").split("/")[-1]
    value = "".join(ch if ch.isalnum() or ch in "._- " else "-" for ch in value).strip(" .-")
    return value[:180] or "item"


def _scoped_models():
    excluded_apps = {"archive_restore", "admin", "auth", "contenttypes", "sessions"}
    selected = []
    for model in apps.get_models():
        if model._meta.app_label in excluded_apps:
            continue
        if model is Wedding:
            selected.append(model)
            continue
        field_names = {field.name for field in model._meta.fields}
        if "wedding" in field_names:
            selected.append(model)
    return selected


def _query_for_wedding(model, wedding):
    if model is Wedding:
        return model._default_manager.filter(pk=wedding.pk)
    queryset = model._default_manager.filter(wedding=wedding)
    if model._meta.label_lower == "integrations.storedobject":
        queryset = queryset.exclude(category=StoredObject.Category.ARCHIVE)
    return queryset


def _serialize_dataset(wedding):
    dataset = {}
    object_count = 0
    exported_objects = []
    for model in _scoped_models():
        queryset = _query_for_wedding(model, wedding).order_by("pk")
        objects = list(queryset)
        if not objects:
            continue
        label = model._meta.label_lower
        payload = json.loads(serializers.serialize("json", objects))
        dataset[label] = payload
        object_count += len(payload)
        exported_objects.extend(objects)
    return dataset, object_count, exported_objects


def _write_legacy_file_fields(archive, exported_objects, manifest_files, written_source_keys, size_state):
    for obj in exported_objects:
        if obj._meta.label_lower == "photos.weddingphoto" and getattr(obj, "storage_object_id", None):
            # v12.1 storage registry is the source of truth for this photo.
            continue
        for field in obj._meta.fields:
            if not isinstance(field, FileField):
                continue
            field_file = getattr(obj, field.name, None)
            if not field_file or not getattr(field_file, "name", ""):
                continue
            source_key = f"filefield:{obj._meta.label_lower}:{obj.pk}:{field.name}:{field_file.name}"
            if source_key in written_source_keys:
                continue
            try:
                field_file.open("rb")
                content = field_file.read()
            except Exception as exc:
                raise ArchiveError(f"Could not read {obj._meta.label_lower} #{obj.pk} file '{field.name}': {exc}") from exc
            finally:
                try:
                    field_file.close()
                except Exception:
                    pass
            member = "/".join([
                "files", "legacy", obj._meta.app_label, obj._meta.model_name,
                str(obj.pk), _safe_member(Path(field_file.name).name),
            ])
            size_state[0] += len(content)
            _enforce_max(size_state[0])
            archive.writestr(member, content)
            manifest_files.append({
                "kind": "file_field",
                "member": member,
                "model": obj._meta.label_lower,
                "object_pk": str(obj.pk),
                "field": field.name,
                "source_name": field_file.name,
                "size": len(content),
                "sha256": _sha256(content),
            })
            written_source_keys.add(source_key)


def _write_stored_objects(archive, wedding, manifest_files, written_source_keys, size_state):
    records = StoredObject.objects.filter(
        wedding=wedding,
        status=StoredObject.Status.AVAILABLE,
    ).exclude(category=StoredObject.Category.ARCHIVE).order_by("pk")
    for record in records:
        source_key = f"stored:{record.pk}"
        if source_key in written_source_keys:
            continue
        try:
            content = read_stored_object(record)
        except Exception as exc:
            raise ArchiveError(f"Could not read stored object #{record.pk} ({record.relative_path}): {exc}") from exc
        member = "/".join([
            "files", "stored", str(record.pk), _safe_member(Path(record.relative_path).name),
        ])
        size_state[0] += len(content)
        _enforce_max(size_state[0])
        archive.writestr(member, content)
        manifest_files.append({
            "kind": "stored_object",
            "member": member,
            "stored_object_id": record.pk,
            "backend": record.backend,
            "category": record.category,
            "relative_path": record.relative_path,
            "remote_item_id": record.remote_item_id,
            "mime_type": record.mime_type,
            "size": len(content),
            "sha256": _sha256(content),
        })
        written_source_keys.add(source_key)


def _enforce_max(size_bytes):
    maximum = int(getattr(settings, "EVERAFTER_ARCHIVE_MAX_BYTES", DEFAULT_MAX_BYTES))
    if maximum > 0 and size_bytes > maximum:
        raise ArchiveError(
            f"Archive source files exceed the configured limit of {maximum / (1024 * 1024):.0f} MB. "
            "Increase EVERAFTER_ARCHIVE_MAX_BYTES only after confirming server memory/storage capacity."
        )


def build_snapshot(*, wedding, actor=None):
    snapshot = ArchiveSnapshot.objects.create(
        wedding=wedding,
        wedding_public_id=wedding.public_id,
        wedding_name=wedding.name,
        status=ArchiveSnapshot.Status.BUILDING,
        created_by=actor,
    )
    _event(snapshot, ArchiveEvent.Action.EXPORT_STARTED, actor, "Archive export started.")

    temp_path = None
    try:
        dataset, object_count, exported_objects = _serialize_dataset(wedding)
        data_bytes = _json_bytes({
            "format": ARCHIVE_FORMAT,
            "wedding_public_id": wedding.public_id,
            "models": dataset,
        })
        _enforce_max(len(data_bytes))

        manifest_files = []
        size_state = [len(data_bytes)]
        written_source_keys = set()
        with tempfile.NamedTemporaryFile(prefix="everafter_archive_", suffix=".zip", delete=False) as temp:
            temp_path = temp.name
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            archive.writestr("data.json", data_bytes)
            _write_stored_objects(archive, wedding, manifest_files, written_source_keys, size_state)
            _write_legacy_file_fields(archive, exported_objects, manifest_files, written_source_keys, size_state)
            manifest = {
                "format": ARCHIVE_FORMAT,
                "created_at": timezone.now().isoformat(),
                "wedding_public_id": wedding.public_id,
                "wedding_name": wedding.name,
                "snapshot_public_id": snapshot.public_id,
                "data_sha256": _sha256(data_bytes),
                "data_object_count": object_count,
                "file_count": len(manifest_files),
                "files": manifest_files,
                "restore_policy": "non-destructive workspace restore; no automatic database purge",
            }
            archive.writestr("manifest.json", _json_bytes(manifest))

        archive_bytes = Path(temp_path).read_bytes()
        relative_path = f"archives/{wedding.public_id}/{snapshot.public_id}.zip"
        record = store_bytes(
            wedding=wedding,
            relative_path=relative_path,
            content=archive_bytes,
            category=StoredObject.Category.ARCHIVE,
            source_app="archive_restore",
            source_model="ArchiveSnapshot",
            source_object_id=snapshot.public_id,
            created_by=actor,
            content_type="application/zip",
        )
        snapshot.stored_object = record
        snapshot.archive_size = len(archive_bytes)
        snapshot.sha256 = _sha256(archive_bytes)
        snapshot.data_object_count = object_count
        snapshot.file_count = len(manifest_files)
        snapshot.manifest = manifest
        snapshot.status = ArchiveSnapshot.Status.READY
        snapshot.last_error = ""
        snapshot.save()
        verify_snapshot(snapshot, actor=actor)
        _event(snapshot, ArchiveEvent.Action.EXPORT_READY, actor, "Archive export completed and verified.")
        return snapshot
    except Exception as exc:
        snapshot.status = ArchiveSnapshot.Status.FAILED
        snapshot.last_error = str(exc)[:1000]
        snapshot.save(update_fields=["status", "last_error", "updated_at"])
        _event(snapshot, ArchiveEvent.Action.EXPORT_FAILED, actor, str(exc))
        raise
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


def verify_snapshot(snapshot, *, actor=None):
    if not snapshot.stored_object_id:
        raise ArchiveError("Archive storage object is missing.")
    try:
        content = read_stored_object(snapshot.stored_object)
        if snapshot.sha256 and _sha256(content) != snapshot.sha256:
            raise ArchiveError("Outer archive SHA-256 does not match the recorded checksum.")
        import io
        with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
            names = set(archive.namelist())
            if "manifest.json" not in names or "data.json" not in names:
                raise ArchiveError("Archive is missing manifest.json or data.json.")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if manifest.get("format") != ARCHIVE_FORMAT:
                raise ArchiveError("Unsupported archive format.")
            if manifest.get("wedding_public_id") != snapshot.wedding_public_id:
                raise ArchiveError("Archive wedding ID does not match this snapshot.")
            data = archive.read("data.json")
            if _sha256(data) != manifest.get("data_sha256"):
                raise ArchiveError("data.json checksum verification failed.")
            for item in manifest.get("files", []):
                member = item.get("member")
                if not member or member not in names:
                    raise ArchiveError(f"Archive member missing: {member or 'unknown'}")
                file_bytes = archive.read(member)
                if len(file_bytes) != int(item.get("size", -1)):
                    raise ArchiveError(f"Archive member size mismatch: {member}")
                if _sha256(file_bytes) != item.get("sha256"):
                    raise ArchiveError(f"Archive member checksum mismatch: {member}")
        snapshot.manifest = manifest
        snapshot.verified_at = timezone.now()
        if snapshot.status != ArchiveSnapshot.Status.RESTORED:
            snapshot.status = ArchiveSnapshot.Status.READY
        snapshot.last_error = ""
        snapshot.save(update_fields=["manifest", "verified_at", "status", "last_error", "updated_at"])
        _event(snapshot, ArchiveEvent.Action.VERIFIED, actor, "Archive checksum verification passed.")
        return True
    except Exception as exc:
        snapshot.status = ArchiveSnapshot.Status.VERIFY_FAILED
        snapshot.verified_at = None
        snapshot.last_error = str(exc)[:1000]
        snapshot.save(update_fields=["status", "verified_at", "last_error", "updated_at"])
        _event(snapshot, ArchiveEvent.Action.VERIFY_FAILED, actor, str(exc))
        raise


@transaction.atomic
def mark_wedding_archived(snapshot, *, actor=None):
    if not snapshot.is_verified:
        raise ArchiveError("Verify the export before archiving the wedding.")
    if not snapshot.wedding_id:
        raise ArchiveError("The wedding workspace no longer exists in this database.")
    wedding = Wedding.objects.select_for_update().get(pk=snapshot.wedding_id)
    wedding.status = Wedding.Status.ARCHIVED
    wedding.archived_at = timezone.now()
    wedding.save(update_fields=["status", "archived_at", "updated_at"])
    _event(snapshot, ArchiveEvent.Action.ARCHIVED, actor, "Wedding workspace marked Archived after verified export.")
    return wedding


@transaction.atomic
def restore_existing_workspace(snapshot, *, actor=None):
    """Restore an existing non-destructively archived workspace to DRAFT.

    v13.0 intentionally does not purge relational rows, so the safest restore is to
    reopen the retained workspace in DRAFT. This prevents invitations from becoming
    public again without an Owner review/publish step.
    """
    if not snapshot.is_verified:
        verify_snapshot(snapshot, actor=actor)
    if not snapshot.wedding_id:
        raise ArchiveError(
            "This v13.0 snapshot has no retained wedding row to reopen. Full recreation after a future purge is not enabled in this milestone."
        )
    wedding = Wedding.objects.select_for_update().get(pk=snapshot.wedding_id)
    snapshot.status = ArchiveSnapshot.Status.RESTORING
    snapshot.save(update_fields=["status", "updated_at"])
    wedding.status = Wedding.Status.DRAFT
    wedding.archived_at = None
    wedding.save(update_fields=["status", "archived_at", "updated_at"])
    snapshot.status = ArchiveSnapshot.Status.RESTORED
    snapshot.restored_at = timezone.now()
    snapshot.last_error = ""
    snapshot.save(update_fields=["status", "restored_at", "last_error", "updated_at"])
    _event(snapshot, ArchiveEvent.Action.RESTORED, actor, "Retained wedding workspace restored to Draft for Owner review.")
    return wedding


@transaction.atomic
def mark_delete_pending(snapshot, *, actor=None):
    if not snapshot.is_verified:
        raise ArchiveError("A verified archive is required before Delete Pending.")
    if not snapshot.wedding_id:
        raise ArchiveError("Wedding workspace is already absent.")
    wedding = Wedding.objects.select_for_update().get(pk=snapshot.wedding_id)
    wedding.status = Wedding.Status.DELETE_PENDING
    wedding.save(update_fields=["status", "updated_at"])
    _event(
        snapshot,
        ArchiveEvent.Action.DELETE_PENDING,
        actor,
        "Wedding marked Delete Pending. v13.0 does not automatically purge database rows or storage files.",
    )
    return wedding
