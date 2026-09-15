import hashlib
import mimetypes
import os
import re
from dataclasses import dataclass

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .graph import OneDriveGraphClient, get_graph_config
from .models import StoredObject, WeddingStorageSettings


SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._ -]+")


class StorageBackendError(RuntimeError):
    pass


def safe_segment(value, fallback="item"):
    value = SAFE_SEGMENT.sub("-", str(value or "")).strip(" .-")
    return value[:120] or fallback


def wedding_remote_root(wedding, settings_obj=None):
    settings_obj = settings_obj or WeddingStorageSettings.objects.get_or_create(wedding=wedding)[0]
    configured_root = (settings_obj.root_folder or "").strip(" /\\")
    if configured_root:
        return "/".join(safe_segment(p) for p in configured_root.replace("\\", "/").split("/") if p)
    graph_root = get_graph_config(drive_id_override=settings_obj.onedrive_drive_id).root_folder
    return "/".join(filter(None, [safe_segment(graph_root, "EverVow"), safe_segment(wedding.public_id, "wedding")]))


@dataclass
class StorageResult:
    backend: str
    relative_path: str
    size_bytes: int
    sha256: str
    mime_type: str
    remote_item_id: str = ""
    remote_web_url: str = ""


class LocalMediaBackend:
    key = WeddingStorageSettings.Provider.LOCAL

    def save(self, *, wedding, relative_path, content, content_type=""):
        relative_path = relative_path.replace("\\", "/").lstrip("/")
        logical_path = "/".join(filter(None, ["weddings", safe_segment(wedding.public_id, "wedding"), relative_path]))
        digest = hashlib.sha256(content).hexdigest()
        mime_type = content_type or mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
        saved_name = default_storage.save(logical_path, ContentFile(content))
        return StorageResult(
            backend=self.key,
            relative_path=saved_name,
            size_bytes=len(content),
            sha256=digest,
            mime_type=mime_type,
        )

    def read(self, record):
        with default_storage.open(record.relative_path, "rb") as handle:
            return handle.read()

    def delete(self, record):
        if default_storage.exists(record.relative_path):
            default_storage.delete(record.relative_path)
        return True


class OneDriveStorageBackend:
    key = WeddingStorageSettings.Provider.ONEDRIVE

    def __init__(self, *, settings_obj):
        self.settings_obj = settings_obj
        config = get_graph_config(drive_id_override=settings_obj.onedrive_drive_id)
        self.client = OneDriveGraphClient(config)

    def save(self, *, wedding, relative_path, content, content_type=""):
        relative_path = relative_path.replace("\\", "/").lstrip("/")
        digest = hashlib.sha256(content).hexdigest()
        mime_type = content_type or mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
        remote_path = "/".join(filter(None, [wedding_remote_root(wedding, self.settings_obj), relative_path]))
        item = self.client.upload_bytes(remote_path, content, content_type=mime_type)
        return StorageResult(
            backend=self.key,
            relative_path=remote_path,
            size_bytes=len(content),
            sha256=digest,
            mime_type=mime_type,
            remote_item_id=item.get("id", ""),
            remote_web_url=item.get("webUrl", ""),
        )

    def read(self, record):
        if not record.remote_item_id:
            raise StorageBackendError("OneDrive object has no remote item ID.")
        return self.client.download_bytes(record.remote_item_id)

    def delete(self, record):
        if not record.remote_item_id:
            raise StorageBackendError("OneDrive object has no remote item ID.")
        return self.client.delete_item(record.remote_item_id)


def backend_for_wedding(wedding):
    settings_obj, _ = WeddingStorageSettings.objects.get_or_create(wedding=wedding)
    if settings_obj.provider == WeddingStorageSettings.Provider.ONEDRIVE:
        return OneDriveStorageBackend(settings_obj=settings_obj)
    return LocalMediaBackend()


def store_bytes(
    *, wedding, relative_path, content, category=StoredObject.Category.OTHER,
    source_app="", source_model="", source_object_id="", created_by=None,
    content_type="",
):
    backend = backend_for_wedding(wedding)
    record = StoredObject.objects.create(
        wedding=wedding,
        backend=backend.key,
        category=category,
        relative_path=relative_path,
        source_app=source_app,
        source_model=source_model,
        source_object_id=str(source_object_id or ""),
        created_by=created_by,
        status=StoredObject.Status.PENDING,
    )
    try:
        result = backend.save(
            wedding=wedding,
            relative_path=relative_path,
            content=content,
            content_type=content_type,
        )
        record.relative_path = result.relative_path
        record.remote_item_id = result.remote_item_id
        record.remote_web_url = result.remote_web_url
        record.mime_type = result.mime_type
        record.size_bytes = result.size_bytes
        record.sha256 = result.sha256
        record.status = StoredObject.Status.AVAILABLE
        record.last_error = ""
        record.save()
        return record
    except Exception as exc:
        record.status = StoredObject.Status.FAILED
        record.last_error = str(exc)[:500]
        record.save(update_fields=["status", "last_error", "updated_at"])
        raise


def backend_for_record(record):
    if record.backend == StoredObject.Backend.ONEDRIVE:
        settings_obj, _ = WeddingStorageSettings.objects.get_or_create(wedding=record.wedding)
        return OneDriveStorageBackend(settings_obj=settings_obj)
    return LocalMediaBackend()


def read_stored_object(record):
    if record.status != StoredObject.Status.AVAILABLE:
        raise StorageBackendError("Storage object is not available.")
    return backend_for_record(record).read(record)


def delete_stored_object(record):
    if record.status == StoredObject.Status.DELETED:
        return record
    backend_for_record(record).delete(record)
    record.status = StoredObject.Status.DELETED
    record.last_error = ""
    record.save(update_fields=["status", "last_error", "updated_at"] )
    return record


def local_storage_summary():
    root = str(getattr(settings, "MEDIA_ROOT", ""))
    return {"media_root": root, "exists": bool(root and os.path.exists(root))}
