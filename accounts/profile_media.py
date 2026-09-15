import hashlib
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse

from integrations.graph import OneDriveGraphClient, get_graph_config
from integrations.storage import safe_segment

from .models import ProfileImageAsset


MAX_PROFILE_IMAGE_BYTES = 20 * 1024 * 1024
MAX_THUMBNAIL_CACHE_BYTES = 2 * 1024 * 1024


def _detect_image(data):
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif", "image/gif"
    return None, None


def validate_profile_upload(uploaded):
    if uploaded is None:
        raise ValueError("Choose a profile photo first.")
    if getattr(uploaded, "size", 0) > MAX_PROFILE_IMAGE_BYTES:
        raise ValueError("Profile photo must be 20 MB or smaller.")
    try:
        uploaded.seek(0)
    except Exception:
        pass
    data = uploaded.read(MAX_PROFILE_IMAGE_BYTES + 1)
    if len(data) > MAX_PROFILE_IMAGE_BYTES:
        raise ValueError("Profile photo must be 20 MB or smaller.")
    if not data:
        raise ValueError("The selected profile photo is empty.")
    suffix, mime_type = _detect_image(data)
    if not suffix:
        raise ValueError("Use a JPG, PNG, WebP, or GIF image.")
    return data, suffix, mime_type


def _profile_root(user):
    config = get_graph_config()
    root = safe_segment(config.root_folder or "EverVow", "EverVow")
    return f"{root}/users/{user.pk}/profile"


def _cache_root():
    configured = getattr(settings, "EVERVOW_THUMBNAIL_CACHE_ROOT", None)
    if configured is None:
        configured = getattr(settings, "EVERAFTER_THUMBNAIL_CACHE_ROOT", None)
    return Path(configured or (settings.BASE_DIR / "media_cache"))


def _cache_path(asset):
    digest = (asset.sha256 or f"item-{asset.pk}")[:20]
    return _cache_root() / "profile" / f"user-{asset.user_id}-{digest}.jpg"


def _clear_profile_cache(user_id):
    folder = _cache_root() / "profile"
    if not folder.exists():
        return
    for path in folder.glob(f"user-{user_id}-*.jpg"):
        try:
            path.unlink()
        except OSError:
            pass


def store_profile_image(*, user, uploaded):
    """Store the original in OneDrive and keep only metadata + thumbnail cache locally."""
    data, suffix, mime_type = validate_profile_upload(uploaded)
    config = get_graph_config()
    client = OneDriveGraphClient(config)

    # Fail early with a clear Graph/drive error before creating any DB metadata.
    client.health_check()

    remote_path = f"{_profile_root(user)}/{uuid.uuid4().hex}{suffix}"
    item = client.upload_bytes(remote_path, data, content_type=mime_type)
    item_id = item.get("id", "")
    if not item_id:
        raise RuntimeError("OneDrive upload returned no item ID.")

    old = ProfileImageAsset.objects.filter(user=user).first()
    old_item_id = old.remote_item_id if old else ""
    old_drive_id = old.drive_id if old else ""

    try:
        with transaction.atomic():
            asset, _created = ProfileImageAsset.objects.update_or_create(
                user=user,
                defaults={
                    "drive_id": config.drive_id,
                    "remote_item_id": item_id,
                    "remote_path": remote_path,
                    "remote_web_url": item.get("webUrl", ""),
                    "mime_type": mime_type,
                    "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
            )
    except Exception:
        # Never leave a newly uploaded orphan if DB persistence fails.
        try:
            client.delete_item(item_id)
        except Exception:
            pass
        raise

    _clear_profile_cache(user.pk)

    if old_item_id and old_item_id != item_id:
        try:
            old_config = get_graph_config(drive_id_override=old_drive_id)
            OneDriveGraphClient(old_config).delete_item(old_item_id)
        except Exception:
            # Replacing the DB pointer is more important than blocking the user because
            # a previous remote object could not be cleaned up immediately.
            pass
    return asset


def remove_profile_image(user):
    asset = ProfileImageAsset.objects.filter(user=user).first()
    if not asset:
        return False
    try:
        config = get_graph_config(drive_id_override=asset.drive_id)
        OneDriveGraphClient(config).delete_item(asset.remote_item_id)
    except Exception:
        pass
    _clear_profile_cache(user.pk)
    asset.delete()
    return True


def profile_thumbnail_response(user):
    asset = ProfileImageAsset.objects.filter(user=user).first()
    if not asset or not asset.remote_item_id:
        raise Http404("Profile photo not found")
    cache_path = _cache_path(asset)
    if cache_path.exists():
        data = cache_path.read_bytes()
        mime_type = "image/jpeg"
        cached = True
    else:
        config = get_graph_config(drive_id_override=asset.drive_id)
        client = OneDriveGraphClient(config)
        cached = False
        try:
            data = client.download_thumbnail_bytes(asset.remote_item_id, size="small")
            mime_type = "image/jpeg"
            if data and len(data) <= MAX_THUMBNAIL_CACHE_BYTES:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache_path.with_suffix(".tmp")
                tmp.write_bytes(data)
                os.replace(tmp, cache_path)
                cached = True
        except Exception:
            data = client.download_bytes(asset.remote_item_id)
            mime_type = asset.mime_type or "application/octet-stream"
    response = HttpResponse(data, content_type=mime_type)
    response["Content-Disposition"] = 'inline; filename="profile-thumbnail"'
    response["Cache-Control"] = "private, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-EverVow-Media"] = "thumbnail-cache" if cached else "onedrive-stream"
    return response
