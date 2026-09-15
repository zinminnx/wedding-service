import hashlib
from io import BytesIO
from pathlib import Path

from django.core.files.storage import default_storage

from integrations.models import StoredObject, WeddingStorageSettings
from integrations.image_media import store_image_bytes
from integrations.storage import delete_stored_object, read_stored_object, store_bytes

from .models import WeddingPhoto, generate_photo_public_id


def _safe_suffix(filename):
    suffix = Path(filename or "").suffix.lower()
    if len(suffix) > 10:
        return ""
    return suffix


def create_photo_with_storage(*, wedding, uploaded, source, status, guest=None, invitation=None,
                              uploaded_by=None, caption="", approved_at=None):
    """Store photo bytes through the v12 storage abstraction, then create WeddingPhoto.

    For LOCAL storage, WeddingPhoto.image points at the exact same stored file for
    backward compatibility. For OneDrive, image stays empty and storage_object is
    the source of truth.
    """
    original_name = Path(uploaded.name or "photo").name[:255] or "photo"
    content_type = (getattr(uploaded, "content_type", "") or "")[:80]
    content = uploaded.read()
    public_id = generate_photo_public_id()
    suffix = _safe_suffix(original_name)
    relative_path = f"photos/{public_id}{suffix}"

    record = store_image_bytes(
        wedding=wedding,
        relative_path=relative_path,
        content=content,
        category=StoredObject.Category.PHOTO,
        source_app="photos",
        source_model="WeddingPhoto",
        source_object_id=public_id,
        created_by=uploaded_by,
        content_type=content_type,
    )

    image_name = record.relative_path if record.backend == StoredObject.Backend.LOCAL else ""
    try:
        photo = WeddingPhoto.objects.create(
            public_id=public_id,
            wedding=wedding,
            guest=guest,
            invitation=invitation,
            uploaded_by=uploaded_by,
            source=source,
            image=image_name,
            storage_object=record,
            original_filename=original_name,
            mime_type=content_type or record.mime_type,
            file_size=len(content),
            caption=(caption or "")[:280],
            status=status,
            approved_at=approved_at,
        )
        return photo
    except Exception:
        try:
            delete_stored_object(record)
        except Exception:
            pass
        raise


def read_photo_bytes(photo):
    if photo.storage_object_id:
        return read_stored_object(photo.storage_object)
    if photo.image:
        photo.image.open("rb")
        try:
            return photo.image.read()
        finally:
            try:
                photo.image.close()
            except Exception:
                pass
    raise FileNotFoundError("Photo file is not available.")


def delete_photo_file(photo):
    """Delete current storage object first, then let caller delete the DB photo row.

    If remote deletion fails, the exception is propagated so we do not silently
    orphan a OneDrive object while deleting the source database record.
    """
    if photo.storage_object_id:
        delete_stored_object(photo.storage_object)
        return
    if photo.image:
        photo.image.delete(save=False)


def photo_content_type(photo):
    if photo.mime_type:
        return photo.mime_type
    if photo.storage_object_id and photo.storage_object.mime_type:
        return photo.storage_object.mime_type
    return "application/octet-stream"


def migrate_photo_to_selected_backend(photo, *, delete_local_after_verify=False):
    """Move one photo to the wedding's selected backend with read-back verification.

    LOCAL -> ONEDRIVE migration is the main use case. Existing local data is kept by
    default. If delete_local_after_verify is requested, the old local file is removed
    only after the new object is downloaded again and its SHA-256 matches.
    """
    settings_obj, _ = WeddingStorageSettings.objects.get_or_create(wedding=photo.wedding)
    target = settings_obj.provider
    current = photo.storage_object.backend if photo.storage_object_id else StoredObject.Backend.LOCAL
    if current == target and photo.storage_object_id:
        return photo.storage_object, False

    content = read_photo_bytes(photo)
    suffix = _safe_suffix(photo.original_filename)
    new_record = store_bytes(
        wedding=photo.wedding,
        relative_path=f"photos/{photo.public_id}{suffix}",
        content=content,
        category=StoredObject.Category.PHOTO,
        source_app="photos",
        source_model="WeddingPhoto",
        source_object_id=photo.public_id,
        created_by=photo.uploaded_by,
        content_type=photo.mime_type,
    )
    verified = hashlib.sha256(read_stored_object(new_record)).hexdigest() == new_record.sha256
    if not verified:
        try:
            delete_stored_object(new_record)
        finally:
            raise RuntimeError(f"Verification failed for {photo.public_id}; source file was kept.")

    old_record = photo.storage_object if photo.storage_object_id else None
    old_image_name = photo.image.name if photo.image else ""

    photo.storage_object = new_record
    if new_record.backend == StoredObject.Backend.LOCAL:
        photo.image.name = new_record.relative_path
    elif delete_local_after_verify:
        photo.image = ""
    photo.save(update_fields=["storage_object", "image", "updated_at"])

    if delete_local_after_verify and new_record.backend == StoredObject.Backend.ONEDRIVE:
        if old_record and old_record.backend == StoredObject.Backend.LOCAL:
            delete_stored_object(old_record)
        elif old_image_name and default_storage.exists(old_image_name):
            default_storage.delete(old_image_name)

    return new_record, True
