import tempfile
from io import BytesIO
import zipfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from invitations.models import Invitation
from staffing.access import (
    PERM_MANAGE_WEDDING,
    PERM_PHOTO,
    get_wedding_for_user,
    has_wedding_permission,
)

from .models import WeddingPhoto, WeddingPhotoSettings
from .storage_backend import (
    create_photo_with_storage,
    delete_photo_file,
    photo_content_type,
    read_photo_bytes,
)


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


def _settings_for(wedding):
    settings_obj, _ = WeddingPhotoSettings.objects.get_or_create(wedding=wedding)
    return settings_obj


def _safe_name(name, fallback="photo"):
    name = Path(name or fallback).name.strip()
    return name or fallback


def _validate_upload(uploaded, photo_settings):
    extension = Path(uploaded.name or "").suffix.lower()
    content_type = (getattr(uploaded, "content_type", "") or "").lower()
    if extension not in ALLOWED_EXTENSIONS:
        return "Only JPG, PNG, WEBP and GIF images are accepted."
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        return "That file does not look like a supported image."
    max_bytes = max(int(photo_settings.max_upload_mb or 1), 1) * 1024 * 1024
    if uploaded.size > max_bytes:
        return f"{uploaded.name} is larger than {photo_settings.max_upload_mb} MB."
    if uploaded.size <= 0:
        return f"{uploaded.name} is empty."
    return ""


def _remaining_capacity(wedding):
    current = WeddingPhoto.objects.filter(wedding=wedding).count()
    limit = max(int(wedding.photo_limit or 0), 0)
    return max(limit - current, 0), current, limit


def _photo_status_for_upload(photo_settings):
    if photo_settings.moderation_required:
        return WeddingPhoto.Status.PENDING
    return WeddingPhoto.Status.APPROVED


def _create_photo(*, wedding, photo_settings, uploaded, source, guest=None, invitation=None, uploaded_by=None, caption=""):
    status = _photo_status_for_upload(photo_settings)
    now = timezone.now()
    return create_photo_with_storage(
        wedding=wedding,
        uploaded=uploaded,
        source=source,
        status=status,
        guest=guest,
        invitation=invitation,
        uploaded_by=uploaded_by,
        caption=caption,
        approved_at=now if status == WeddingPhoto.Status.APPROVED else None,
    )


def _staff_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_PHOTO)
    if not wedding:
        raise Http404("Wedding not found")
    return wedding


def _staff_photo(request, public_id):
    wedding = _staff_wedding(request)
    return get_object_or_404(
        WeddingPhoto.objects.select_related("guest", "wedding", "storage_object"),
        wedding=wedding,
        public_id=public_id,
    )


def _delete_photo(photo):
    delete_photo_file(photo)
    photo.delete()


def _set_status(photo, status, user):
    now = timezone.now()
    photo.status = status
    photo.moderated_by = user
    photo.moderated_at = now
    photo.approved_at = now if status == WeddingPhoto.Status.APPROVED else None
    photo.save(update_fields=["status", "moderated_by", "moderated_at", "approved_at", "updated_at"])


def _zip_response(photos, filename):
    stream = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024, mode="w+b")
    used_names = set()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for photo in photos:
            original = _safe_name(photo.original_filename, f"{photo.public_id}.jpg")
            stem = Path(original).stem[:120] or photo.public_id
            suffix = Path(original).suffix[:10]
            member_name = f"{stem}{suffix}"
            if member_name.lower() in used_names:
                member_name = f"{stem}-{photo.public_id}{suffix}"
            used_names.add(member_name.lower())
            try:
                archive.writestr(member_name, read_photo_bytes(photo))
            except Exception:
                continue
    stream.seek(0)
    return FileResponse(stream, as_attachment=True, filename=filename, content_type="application/zip")


def _inline_photo_response(photo):
    try:
        content = read_photo_bytes(photo)
    except Exception as exc:
        raise Http404("Photo file not found") from exc
    response = FileResponse(BytesIO(content), content_type=photo_content_type(photo))
    response["Content-Disposition"] = f'inline; filename="{_safe_name(photo.original_filename, photo.public_id)}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def dashboard(request):
    wedding = _staff_wedding(request)
    photo_settings = _settings_for(wedding)

    photos = WeddingPhoto.objects.filter(wedding=wedding).select_related("guest", "moderated_by", "storage_object")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip().upper()
    source = request.GET.get("source", "").strip().upper()

    if q:
        photos = photos.filter(
            Q(public_id__icontains=q)
            | Q(guest__name__icontains=q)
            | Q(guest__phone__icontains=q)
            | Q(original_filename__icontains=q)
            | Q(caption__icontains=q)
        )
    if status in WeddingPhoto.Status.values:
        photos = photos.filter(status=status)
    if source in WeddingPhoto.Source.values:
        photos = photos.filter(source=source)

    all_photos = WeddingPhoto.objects.filter(wedding=wedding)
    counts = {
        "all": all_photos.count(),
        "pending": all_photos.filter(status=WeddingPhoto.Status.PENDING).count(),
        "approved": all_photos.filter(status=WeddingPhoto.Status.APPROVED).count(),
        "rejected": all_photos.filter(status=WeddingPhoto.Status.REJECTED).count(),
    }
    remaining, current, limit = _remaining_capacity(wedding)
    slideshow_url = request.build_absolute_uri(
        reverse("photos:slideshow", args=[photo_settings.slideshow_token])
    )

    return render(
        request,
        "photos/dashboard.html",
        {
            "wedding": wedding,
            "photo_settings": photo_settings,
            "photos": photos[:300],
            "counts": counts,
            "remaining": remaining,
            "current_photo_count": current,
            "photo_limit": limit,
            "slideshow_url": slideshow_url,
            "can_manage_settings": has_wedding_permission(request.user, wedding, PERM_MANAGE_WEDDING),
            "status_choices": WeddingPhoto.Status.choices,
            "source_choices": WeddingPhoto.Source.choices,
            "q": q,
            "status_filter": status,
            "source_filter": source,
        },
    )


@login_required
def update_settings(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _staff_wedding(request)
    if not has_wedding_permission(request.user, wedding, PERM_MANAGE_WEDDING):
        raise Http404("Wedding not found")

    photo_settings = _settings_for(wedding)
    photo_settings.guest_upload_enabled = request.POST.get("guest_upload_enabled") == "on"
    photo_settings.moderation_required = request.POST.get("moderation_required") == "on"
    photo_settings.slideshow_enabled = request.POST.get("slideshow_enabled") == "on"
    photo_settings.guest_can_download_own = request.POST.get("guest_can_download_own") == "on"
    try:
        photo_settings.max_upload_mb = min(max(int(request.POST.get("max_upload_mb", 15)), 1), 50)
        photo_settings.max_files_per_upload = min(max(int(request.POST.get("max_files_per_upload", 10)), 1), 20)
    except ValueError:
        messages.error(request, "Upload limits must be numbers.")
        return redirect("photos:dashboard")
    photo_settings.save()
    messages.success(request, "Photo settings saved.")
    return redirect("photos:dashboard")


@login_required
def staff_upload(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _staff_wedding(request)
    photo_settings = _settings_for(wedding)
    uploads = request.FILES.getlist("photos")
    caption = request.POST.get("caption", "").strip()

    if not uploads:
        messages.error(request, "Choose at least one photo.")
        return redirect("photos:dashboard")
    if len(uploads) > photo_settings.max_files_per_upload:
        messages.error(request, f"Upload up to {photo_settings.max_files_per_upload} photos at a time.")
        return redirect("photos:dashboard")

    remaining, _, _ = _remaining_capacity(wedding)
    if remaining <= 0:
        messages.error(request, "This wedding has reached its photo package limit.")
        return redirect("photos:dashboard")
    uploads = uploads[:remaining]

    errors = []
    created = 0
    source = WeddingPhoto.Source.OWNER if (request.user.is_superuser or wedding.owner_id == request.user.id) else WeddingPhoto.Source.STAFF
    for uploaded in uploads:
        error = _validate_upload(uploaded, photo_settings)
        if error:
            errors.append(error)
            continue
        try:
            _create_photo(
                wedding=wedding,
                photo_settings=photo_settings,
                uploaded=uploaded,
                source=source,
                uploaded_by=request.user,
                caption=caption,
            )
            created += 1
        except Exception as exc:
            errors.append(f"Storage upload failed for {uploaded.name}: {exc}")

    if created:
        messages.success(request, f"{created} photo(s) uploaded.")
    for error in errors[:4]:
        messages.error(request, error)
    return redirect("photos:dashboard")


@login_required
def photo_action(request, public_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    photo = _staff_photo(request, public_id)
    action = request.POST.get("action", "").strip().lower()

    if action == "approve":
        _set_status(photo, WeddingPhoto.Status.APPROVED, request.user)
        messages.success(request, "Photo approved for the wedding gallery.")
    elif action == "reject":
        _set_status(photo, WeddingPhoto.Status.REJECTED, request.user)
        messages.success(request, "Photo rejected.")
    elif action == "pending":
        _set_status(photo, WeddingPhoto.Status.PENDING, request.user)
        messages.success(request, "Photo moved back to pending review.")
    elif action == "delete":
        _delete_photo(photo)
        messages.success(request, "Photo deleted.")
    else:
        return HttpResponseBadRequest("Unknown action")
    return redirect(request.POST.get("next") or "photos:dashboard")


@login_required
def bulk_action(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _staff_wedding(request)
    selected = request.POST.getlist("photo_ids")
    action = request.POST.get("action", "").strip().lower()

    if action == "download_all":
        all_photos = list(WeddingPhoto.objects.filter(wedding=wedding).select_related("guest"))
        if not all_photos:
            messages.info(request, "There are no wedding photos to download yet.")
            return redirect("photos:dashboard")
        return _zip_response(all_photos, f"{wedding.slug}-all-original-photos.zip")

    photos = list(WeddingPhoto.objects.filter(wedding=wedding, public_id__in=selected).select_related("guest"))
    if not photos:
        messages.info(request, "Select one or more photos first.")
        return redirect("photos:dashboard")

    if action == "download":
        return _zip_response(photos, f"{wedding.slug}-selected-photos.zip")
    if action in {"approve", "reject", "pending"}:
        mapping = {
            "approve": WeddingPhoto.Status.APPROVED,
            "reject": WeddingPhoto.Status.REJECTED,
            "pending": WeddingPhoto.Status.PENDING,
        }
        for photo in photos:
            _set_status(photo, mapping[action], request.user)
        messages.success(request, f"Updated {len(photos)} photo(s).")
        return redirect("photos:dashboard")
    if action == "delete":
        for photo in photos:
            _delete_photo(photo)
        messages.success(request, f"Deleted {len(photos)} photo(s).")
        return redirect("photos:dashboard")
    return HttpResponseBadRequest("Unknown action")


@login_required
def staff_file(request, public_id):
    photo = _staff_photo(request, public_id)
    return _inline_photo_response(photo)


@login_required
def staff_download(request, public_id):
    photo = _staff_photo(request, public_id)
    WeddingPhoto.objects.filter(pk=photo.pk).update(download_count=F("download_count") + 1)
    try:
        content = read_photo_bytes(photo)
    except Exception as exc:
        raise Http404("Photo file not found") from exc
    return FileResponse(
        BytesIO(content),
        as_attachment=True,
        filename=_safe_name(photo.original_filename, f"{photo.public_id}.jpg"),
        content_type=photo_content_type(photo),
    )


def _public_invitation(token):
    invitation = get_object_or_404(
        Invitation.objects.select_related("wedding", "guest"),
        token=token,
    )
    if invitation.status in {Invitation.Status.REVOKED, Invitation.Status.EXPIRED}:
        raise Http404("Invitation is not available")
    return invitation


def guest_gallery(request, token):
    invitation = _public_invitation(token)
    wedding = invitation.wedding
    guest = invitation.guest
    photo_settings = _settings_for(wedding)
    own_photos = WeddingPhoto.objects.filter(
        wedding=wedding,
        guest=guest,
        invitation=invitation,
    ).order_by("-created_at")

    upload_errors = []
    uploaded_count = 0
    if request.method == "POST":
        if not photo_settings.guest_upload_enabled:
            upload_errors.append("Guest photo uploads are currently closed.")
        else:
            uploads = request.FILES.getlist("photos")
            caption = request.POST.get("caption", "").strip()
            if not uploads:
                upload_errors.append("Choose at least one photo.")
            elif len(uploads) > photo_settings.max_files_per_upload:
                upload_errors.append(f"Please upload no more than {photo_settings.max_files_per_upload} photos at once.")
            else:
                remaining, _, _ = _remaining_capacity(wedding)
                if remaining <= 0:
                    upload_errors.append("The wedding photo gallery has reached its upload limit.")
                else:
                    uploads = uploads[:remaining]
                    for uploaded in uploads:
                        error = _validate_upload(uploaded, photo_settings)
                        if error:
                            upload_errors.append(error)
                            continue
                        try:
                            _create_photo(
                                wedding=wedding,
                                photo_settings=photo_settings,
                                uploaded=uploaded,
                                source=WeddingPhoto.Source.GUEST,
                                guest=guest,
                                invitation=invitation,
                                caption=caption,
                            )
                            uploaded_count += 1
                        except Exception as exc:
                            upload_errors.append(f"Storage upload failed for {uploaded.name}: {exc}")
                    if uploaded_count and not upload_errors:
                        return redirect(f"{reverse('photos:guest_upload', args=[token])}?uploaded={uploaded_count}")

    remaining, current, limit = _remaining_capacity(wedding)
    try:
        query_uploaded = int(request.GET.get("uploaded", "0"))
    except ValueError:
        query_uploaded = 0

    return render(
        request,
        "photos/guest_gallery.html",
        {
            "wedding": wedding,
            "guest": guest,
            "invitation": invitation,
            "photo_settings": photo_settings,
            "own_photos": own_photos,
            "upload_errors": upload_errors,
            "uploaded_count": query_uploaded or uploaded_count,
            "remaining": remaining,
            "current_photo_count": current,
            "photo_limit": limit,
        },
    )


def guest_file(request, token, public_id):
    invitation = _public_invitation(token)
    photo = get_object_or_404(
        WeddingPhoto.objects.select_related("storage_object"),
        public_id=public_id,
        wedding=invitation.wedding,
        guest=invitation.guest,
        invitation=invitation,
    )
    return _inline_photo_response(photo)


def guest_download(request, token, public_id):
    invitation = _public_invitation(token)
    photo_settings = _settings_for(invitation.wedding)
    if not photo_settings.guest_can_download_own:
        raise Http404("Downloads are disabled")
    photo = get_object_or_404(
        WeddingPhoto.objects.select_related("storage_object"),
        public_id=public_id,
        wedding=invitation.wedding,
        guest=invitation.guest,
        invitation=invitation,
    )
    WeddingPhoto.objects.filter(pk=photo.pk).update(download_count=F("download_count") + 1)
    try:
        content = read_photo_bytes(photo)
    except Exception as exc:
        raise Http404("Photo file not found") from exc
    return FileResponse(
        BytesIO(content),
        as_attachment=True,
        filename=_safe_name(photo.original_filename, f"{photo.public_id}.jpg"),
        content_type=photo_content_type(photo),
    )


def slideshow(request, token):
    photo_settings = get_object_or_404(
        WeddingPhotoSettings.objects.select_related("wedding"),
        slideshow_token=token,
        slideshow_enabled=True,
    )
    return render(
        request,
        "photos/slideshow.html",
        {
            "wedding": photo_settings.wedding,
            "photo_settings": photo_settings,
        },
    )


def slideshow_file(request, token, public_id):
    photo_settings = get_object_or_404(
        WeddingPhotoSettings.objects.select_related("wedding"),
        slideshow_token=token,
        slideshow_enabled=True,
    )
    photo = get_object_or_404(
        WeddingPhoto.objects.select_related("storage_object"),
        public_id=public_id,
        wedding=photo_settings.wedding,
        status=WeddingPhoto.Status.APPROVED,
    )
    return _inline_photo_response(photo)


def slideshow_feed(request, token):
    photo_settings = get_object_or_404(
        WeddingPhotoSettings.objects.select_related("wedding"),
        slideshow_token=token,
        slideshow_enabled=True,
    )
    photos = WeddingPhoto.objects.filter(
        wedding=photo_settings.wedding,
        status=WeddingPhoto.Status.APPROVED,
    ).order_by("created_at")[:500]
    payload = []
    for photo in photos:
        payload.append(
            {
                "id": photo.public_id,
                "url": request.build_absolute_uri(
                    reverse("photos:slideshow_file", args=[token, photo.public_id])
                ),
                "caption": photo.caption,
                "created_at": photo.created_at.isoformat(),
            }
        )
    return JsonResponse({"photos": payload, "count": len(payload)})
