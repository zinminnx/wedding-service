import uuid

from django.http import Http404, HttpResponse

from integrations.models import StoredObject
from integrations.image_media import store_image_bytes
from integrations.storage import delete_stored_object, read_stored_object


MAX_HERO_IMAGE_BYTES = 12 * 1024 * 1024


def _detect_image(data):
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None, None


def validate_hero_upload(uploaded):
    if uploaded is None:
        raise ValueError("Choose a cover photo first.")
    if getattr(uploaded, "size", 0) > MAX_HERO_IMAGE_BYTES:
        raise ValueError("Cover photo must be 12 MB or smaller.")
    data = uploaded.read(MAX_HERO_IMAGE_BYTES + 1)
    if len(data) > MAX_HERO_IMAGE_BYTES:
        raise ValueError("Cover photo must be 12 MB or smaller.")
    if not data:
        raise ValueError("The selected cover photo is empty.")
    suffix, mime_type = _detect_image(data)
    if not suffix:
        raise ValueError("Use a JPG, PNG, or WebP image.")
    return data, suffix, mime_type


def store_hero_upload(*, wedding, design, uploaded, created_by):
    data, suffix, mime_type = validate_hero_upload(uploaded)
    relative_path = f"invitation/hero/{uuid.uuid4().hex}{suffix}"
    return store_image_bytes(
        wedding=wedding,
        relative_path=relative_path,
        content=data,
        category=StoredObject.Category.OTHER,
        source_app="invitation_themes",
        source_model="WeddingInvitationDesign",
        source_object_id=wedding.public_id,
        created_by=created_by,
        content_type=mime_type,
    )


def published_hero_for_wedding(wedding):
    from .models import WeddingInvitationDesign

    design = (
        WeddingInvitationDesign.objects.select_related("published_hero_image")
        .filter(wedding=wedding)
        .first()
    )
    record = design.published_hero_image if design else None
    if not record or record.wedding_id != wedding.id or record.status != StoredObject.Status.AVAILABLE:
        return None
    return record


def delete_if_unreferenced(record_id):
    if not record_id:
        return
    from .models import WeddingInvitationDesign

    in_use = WeddingInvitationDesign.objects.filter(
        draft_hero_image_id=record_id
    ).exists() or WeddingInvitationDesign.objects.filter(
        published_hero_image_id=record_id
    ).exists()
    if in_use:
        return
    record = StoredObject.objects.filter(pk=record_id).first()
    if not record:
        return
    try:
        delete_stored_object(record)
    except Exception:
        # Data safety first: a storage cleanup failure must not break the user's
        # invitation design workflow. The orphan can be cleaned up later.
        return


def hero_image_response(record, *, cache_control="private, max-age=3600"):
    if not record or record.status != StoredObject.Status.AVAILABLE:
        raise Http404("Cover photo not found")
    try:
        data = read_stored_object(record)
    except Exception as exc:
        raise Http404("Cover photo unavailable") from exc
    response = HttpResponse(data, content_type=record.mime_type or "application/octet-stream")
    response["Content-Disposition"] = 'inline; filename="wedding-cover"'
    response["Cache-Control"] = cache_control
    response["X-Content-Type-Options"] = "nosniff"
    if record.sha256:
        response["ETag"] = f'"{record.sha256}"'
    return response
