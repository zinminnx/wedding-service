import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect

from invitation_themes.models import WeddingInvitationDesign
from integrations.image_media import thumbnail_response_for_record
from staffing.access import accessible_weddings

from .profile_media import profile_thumbnail_response, remove_profile_image, store_profile_image


logger = logging.getLogger(__name__)


@login_required
def profile_photo_upload(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    uploaded = request.FILES.get("profile_image")
    if uploaded is None:
        messages.error(request, "Choose a profile photo before pressing Upload Photo.")
        return redirect("accounts:profile")

    try:
        asset = store_profile_image(user=request.user, uploaded=uploaded)
    except Exception as exc:
        logger.exception("EverVow profile photo upload failed for user_id=%s", request.user.pk)
        messages.error(request, f"Profile photo upload failed: {str(exc) or 'unknown error'}")
    else:
        messages.success(
            request,
            f"Profile photo saved to OneDrive ({asset.size_bytes / 1024:.0f} KB).",
        )
    return redirect("accounts:profile")


@login_required
def profile_photo_remove(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    remove_profile_image(request.user)
    messages.success(request, "Profile photo removed.")
    return redirect("accounts:profile")


@login_required
def profile_thumbnail(request):
    return profile_thumbnail_response(request.user)


@login_required
def wedding_cover_thumbnail(request, wedding_public_id):
    wedding = accessible_weddings(request.user).filter(public_id=wedding_public_id).first()
    if wedding is None:
        raise Http404("Wedding not found")
    design = (
        WeddingInvitationDesign.objects.select_related("draft_hero_image", "published_hero_image")
        .filter(wedding=wedding)
        .first()
    )
    if design is None:
        raise Http404("Cover photo not found")
    record = design.draft_hero_image or design.published_hero_image
    if record is None or record.wedding_id != wedding.id:
        raise Http404("Cover photo not found")
    return thumbnail_response_for_record(
        record,
        namespace="wedding-covers",
        key=wedding.public_id,
    )
