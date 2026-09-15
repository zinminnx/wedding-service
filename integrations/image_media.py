import hashlib
import os
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse

from .graph import OneDriveGraphClient, get_graph_config
from .models import StoredObject, WeddingStorageSettings
from .storage import read_stored_object, safe_segment, wedding_remote_root


MAX_THUMBNAIL_CACHE_BYTES = 2 * 1024 * 1024


def _cache_root():
    configured = getattr(settings, "EVERVOW_THUMBNAIL_CACHE_ROOT", None)
    if configured is None:
        configured = getattr(settings, "EVERAFTER_THUMBNAIL_CACHE_ROOT", None)
    return Path(configured or (settings.BASE_DIR / "media_cache"))


def _atomic_cache_write(path: Path, data: bytes):
    if not data or len(data) > MAX_THUMBNAIL_CACHE_BYTES:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return True


def _wedding_graph_client(wedding):
    storage_settings, _ = WeddingStorageSettings.objects.get_or_create(wedding=wedding)
    config = get_graph_config(drive_id_override=storage_settings.onedrive_drive_id)
    return OneDriveGraphClient(config), storage_settings


def store_image_bytes(
    *, wedding, relative_path, content, category=StoredObject.Category.OTHER,
    source_app="", source_model="", source_object_id="", created_by=None,
    content_type="",
):
    """Store an image original in OneDrive regardless of the wedding's generic file backend.

    This is the v14.1.5 media policy: image originals live in OneDrive. The VPS may
    cache only Graph-generated thumbnails under media_cache/.
    """
    client, storage_settings = _wedding_graph_client(wedding)
    clean_relative = str(relative_path or "").replace("\\", "/").lstrip("/")
    if not clean_relative:
        raise ValueError("Image storage path is required.")
    remote_path = "/".join(
        filter(None, [wedding_remote_root(wedding, storage_settings), clean_relative])
    )
    record = StoredObject.objects.create(
        wedding=wedding,
        backend=StoredObject.Backend.ONEDRIVE,
        category=category,
        relative_path=remote_path,
        source_app=source_app,
        source_model=source_model,
        source_object_id=str(source_object_id or ""),
        created_by=created_by,
        status=StoredObject.Status.PENDING,
    )
    try:
        digest = hashlib.sha256(content).hexdigest()
        item = client.upload_bytes(remote_path, content, content_type=content_type or "application/octet-stream")
        record.remote_item_id = item.get("id", "")
        record.remote_web_url = item.get("webUrl", "")
        record.mime_type = content_type or "application/octet-stream"
        record.size_bytes = len(content)
        record.sha256 = digest
        record.status = StoredObject.Status.AVAILABLE
        record.last_error = ""
        record.save()
        return record
    except Exception as exc:
        record.status = StoredObject.Status.FAILED
        record.last_error = str(exc)[:500]
        record.save(update_fields=["status", "last_error", "updated_at"])
        raise


def _record_cache_path(record, namespace, key):
    digest = (record.sha256 or f"item-{record.pk}")[:20]
    safe_key = safe_segment(key, "image")
    return _cache_root() / safe_segment(namespace, "images") / f"{safe_key}-{digest}.jpg"


def thumbnail_bytes_for_record(record, *, namespace, key):
    if not record or record.status != StoredObject.Status.AVAILABLE:
        raise FileNotFoundError("Image is not available.")

    cache_path = _record_cache_path(record, namespace, key)
    if cache_path.exists():
        return cache_path.read_bytes(), "image/jpeg", True

    if record.backend == StoredObject.Backend.ONEDRIVE and record.remote_item_id:
        try:
            client, _settings_obj = _wedding_graph_client(record.wedding)
            data = client.download_thumbnail_bytes(record.remote_item_id, size="small")
            if _atomic_cache_write(cache_path, data):
                return data, "image/jpeg", True
        except Exception:
            # OneDrive can take a moment to generate a thumbnail after upload.
            # Fall back to streaming the original, but never cache the full file.
            pass

    data = read_stored_object(record)
    return data, record.mime_type or "application/octet-stream", False


def thumbnail_response_for_record(record, *, namespace, key):
    try:
        data, mime_type, cached_thumb = thumbnail_bytes_for_record(
            record, namespace=namespace, key=key
        )
    except Exception as exc:
        raise Http404("Image thumbnail unavailable") from exc
    response = HttpResponse(data, content_type=mime_type)
    response["Content-Disposition"] = 'inline; filename="thumbnail"'
    response["Cache-Control"] = "private, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-EverVow-Media"] = "thumbnail-cache" if cached_thumb else "onedrive-stream"
    return response


def _logical_relative_path(record):
    path = (record.relative_path or "").replace("\\", "/").lstrip("/")
    prefix = f"weddings/{record.wedding.public_id}/"
    if path.startswith(prefix):
        path = path[len(prefix):]
    # If a prior remote-style path somehow reaches here, keep only the useful
    # source family so the new OneDrive path stays inside the wedding root.
    if record.category == StoredObject.Category.PHOTO and "/photos/" in f"/{path}":
        path = "photos/" + path.rsplit("/photos/", 1)[-1]
    elif record.source_app == "invitation_themes" and "/invitation/" in f"/{path}":
        path = "invitation/" + path.rsplit("/invitation/", 1)[-1]
    return path or f"images/{record.pk}"


def migrate_local_image_record_to_onedrive(record, *, delete_local_after_verify=False):
    if record.backend == StoredObject.Backend.ONEDRIVE:
        return record, False
    if record.backend != StoredObject.Backend.LOCAL:
        raise RuntimeError("Unsupported source backend for image migration.")

    old_local_path = record.relative_path
    content = read_stored_object(record)
    client, storage_settings = _wedding_graph_client(record.wedding)
    relative_path = _logical_relative_path(record)
    remote_path = "/".join(
        filter(None, [wedding_remote_root(record.wedding, storage_settings), relative_path])
    )
    item = client.upload_bytes(
        remote_path,
        content,
        content_type=record.mime_type or "application/octet-stream",
    )
    remote_item_id = item.get("id", "")
    if not remote_item_id:
        raise RuntimeError("OneDrive upload returned no item ID; local source was kept.")

    expected = hashlib.sha256(content).hexdigest()
    try:
        downloaded = client.download_bytes(remote_item_id)
        actual = hashlib.sha256(downloaded).hexdigest()
        if actual != expected:
            raise RuntimeError("OneDrive read-back checksum did not match; local source was kept.")
    except Exception:
        try:
            client.delete_item(remote_item_id)
        except Exception:
            pass
        raise

    record.backend = StoredObject.Backend.ONEDRIVE
    record.relative_path = remote_path
    record.remote_item_id = remote_item_id
    record.remote_web_url = item.get("webUrl", "")
    record.size_bytes = len(content)
    record.sha256 = expected
    record.status = StoredObject.Status.AVAILABLE
    record.last_error = ""
    record.save()

    if delete_local_after_verify and old_local_path and default_storage.exists(old_local_path):
        default_storage.delete(old_local_path)
        if record.source_app == "photos" and record.source_model == "WeddingPhoto":
            try:
                from photos.models import WeddingPhoto
                WeddingPhoto.objects.filter(storage_object=record).update(image="")
            except Exception:
                pass
    return record, True
