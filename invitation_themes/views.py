from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from modules.services import module_available
from staffing.access import get_wedding_for_user

from .forms import InvitationCustomizationForm
from .hero_storage import (
    delete_if_unreferenced,
    hero_image_response,
    store_hero_upload,
)
from .models import InvitationTheme
from .sections import SECTION_KEYS, SECTION_MAP, normalize_section_config
from .services import (
    can_publish_draft,
    draft_section_config,
    get_or_create_design,
    selectable_themes,
    studio_section_rows,
)


def _design_wedding(request):
    wedding = get_wedding_for_user(request.user)
    if not wedding:
        raise Http404("Wedding not found")
    is_authority = bool(
        request.user.is_superuser
        or wedding.owner_id == request.user.id
        or getattr(request.user, "role", "") in {"SUPER_ADMIN", "ADMIN"}
    )
    if not is_authority:
        raise Http404("Design Studio unavailable")
    if not module_available("invitation_themes", user=request.user, wedding=wedding, check_role=True):
        messages.warning(request, "Invitation Themes is not available for this wedding package or module setup.")
        return None
    return wedding


@login_required
def design_studio(request):
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    design = get_or_create_design(wedding)
    themes = list(selectable_themes())
    published_legacy = None
    if design.published_theme_id and design.published_theme not in themes:
        published_legacy = design.published_theme

    form = InvitationCustomizationForm(
        theme=design.draft_theme,
        initial=design.draft_customization or {},
    )
    sections = studio_section_rows(design, wedding)
    return render(request, "invitation_themes/studio.html", {
        "wedding": wedding,
        "design": design,
        "themes": themes,
        "published_legacy": published_legacy,
        "customize_form": form,
        "section_rows": sections,
        "enabled_section_count": sum(1 for item in sections if item["enabled"] and item["runtime_available"]),
    })




@login_required
def upload_hero_image(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    design = get_or_create_design(wedding)
    uploaded = request.FILES.get("hero_image")
    try:
        record = store_hero_upload(
            wedding=wedding,
            design=design,
            uploaded=uploaded,
            created_by=request.user,
        )
    except (ValueError, OSError, RuntimeError) as exc:
        messages.error(request, str(exc) or "Cover photo upload failed.")
        return redirect("invitation_themes:studio")

    old_id = design.draft_hero_image_id
    design.draft_hero_image = record
    design.updated_by = request.user
    design.save(update_fields=["draft_hero_image", "updated_by", "updated_at"])
    delete_if_unreferenced(old_id)
    messages.success(request, "Draft cover photo saved. Publish the invitation design to make it live.")
    return redirect("invitation_themes:studio")


@login_required
def remove_hero_image(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    design = get_or_create_design(wedding)
    old_id = design.draft_hero_image_id
    design.draft_hero_image = None
    design.updated_by = request.user
    design.save(update_fields=["draft_hero_image", "updated_by", "updated_at"])
    delete_if_unreferenced(old_id)
    messages.success(request, "Draft cover photo removed. The live invitation is unchanged until you publish.")
    return redirect("invitation_themes:studio")


@login_required
def draft_hero_image(request):
    wedding = _design_wedding(request)
    if wedding is None:
        raise Http404("Wedding not found")
    design = get_or_create_design(wedding)
    record = design.draft_hero_image
    if not record or record.wedding_id != wedding.id:
        raise Http404("Cover photo not found")
    return hero_image_response(record, cache_control="private, no-store")


@login_required
def use_theme(request, theme_key):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    theme = get_object_or_404(
        InvitationTheme,
        key=theme_key,
        status=InvitationTheme.Status.PUBLISHED,
        visible=True,
    )
    design = get_or_create_design(wedding)
    design.draft_theme = theme
    design.draft_customization = {}
    design.draft_sections = normalize_section_config(
        design.draft_sections or design.published_sections,
        supported_sections=theme.supported_sections,
    )
    design.updated_by = request.user
    design.save(update_fields=[
        "draft_theme", "draft_customization", "draft_sections", "updated_by", "updated_at"
    ])
    messages.success(request, f"{theme.name} is now your draft theme. Preview and publish when ready.")
    return redirect("invitation_themes:studio")


@login_required
def customize_theme(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    design = get_or_create_design(wedding)
    if not design.draft_theme:
        messages.error(request, "Choose a theme first.")
        return redirect("invitation_themes:studio")
    form = InvitationCustomizationForm(request.POST, theme=design.draft_theme)
    if form.is_valid():
        design.draft_customization = {key: value for key, value in form.cleaned_data.items() if value}
        design.updated_by = request.user
        design.save(update_fields=["draft_customization", "updated_by", "updated_at"])
        messages.success(request, "Draft customization saved. Live invitations are unchanged until you publish.")
    else:
        messages.error(request, "Please correct the customization fields.")
    return redirect("invitation_themes:studio")


@login_required
def save_sections(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    design = get_or_create_design(wedding)
    if not design.draft_theme:
        messages.error(request, "Choose a theme first.")
        return redirect("invitation_themes:studio")

    posted_order = request.POST.getlist("section_order")
    enabled_keys = set(request.POST.getlist("section_enabled"))
    clean_order = []
    for key in posted_order:
        if key in SECTION_MAP and key not in clean_order:
            clean_order.append(key)
    for key in SECTION_KEYS:
        if key not in clean_order:
            clean_order.append(key)

    current_rows = studio_section_rows(design, wedding)
    availability = {item["key"]: item["runtime_available"] for item in current_rows}
    raw = []
    for index, key in enumerate(clean_order, start=1):
        enabled = key in enabled_keys and availability.get(key, False)
        raw.append({"key": key, "enabled": enabled, "sort_order": index * 10})

    design.draft_sections = normalize_section_config(
        raw,
        supported_sections=design.draft_theme.supported_sections,
    )
    design.updated_by = request.user
    design.save(update_fields=["draft_sections", "updated_by", "updated_at"])
    messages.success(request, "Draft section visibility and order saved. Live invitations are unchanged until publish.")
    return redirect("invitation_themes:studio")


@login_required
def publish_design(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    design = get_or_create_design(wedding)
    if not can_publish_draft(design):
        messages.error(request, "This draft theme is no longer available for new selection. Choose a published theme.")
        return redirect("invitation_themes:studio")
    design.published_theme = design.draft_theme
    design.published_customization = dict(design.draft_customization or {})
    design.published_sections = draft_section_config(design)
    old_published_hero_id = design.published_hero_image_id
    design.published_hero_image = design.draft_hero_image
    design.published_at = timezone.now()
    design.updated_by = request.user
    design.save(update_fields=[
        "published_theme", "published_customization", "published_sections",
        "published_hero_image", "published_at", "updated_by", "updated_at"
    ])
    if old_published_hero_id and old_published_hero_id != design.published_hero_image_id:
        delete_if_unreferenced(old_published_hero_id)
    messages.success(request, f"{design.published_theme.name}, cover photo, and section layout are now live.")
    return redirect("invitation_themes:studio")


@login_required
def preview_theme(request, theme_key):
    wedding = _design_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")
    design = get_or_create_design(wedding)
    theme = InvitationTheme.objects.filter(key=theme_key).first()
    if not theme:
        raise Http404("Theme not found")
    selectable = theme.status == InvitationTheme.Status.PUBLISHED and theme.visible
    already_used = theme.pk in {design.draft_theme_id, design.published_theme_id}
    if not selectable and not already_used:
        raise Http404("Theme unavailable")

    customization = design.draft_customization if design.draft_theme_id == theme.id else {}
    accent = customization.get("accent") or (theme.config or {}).get("accent") or "#B98A45"
    hero_message = customization.get("hero_message") or "A new chapter, together."
    sample_guest = SimpleNamespace(name="Dear Guest", allowed_party_size=2)
    preview_rows = normalize_section_config(
        design.draft_sections or design.published_sections,
        supported_sections=theme.supported_sections,
    )
    preview_sections = [
        {**SECTION_MAP[row["key"]], **row}
        for row in preview_rows
        if row["enabled"]
    ]
    return render(request, "invitation_themes/preview.html", {
        "wedding": wedding,
        "theme": theme,
        "accent": accent,
        "hero_message": hero_message,
        "guest": sample_guest,
        "device": request.GET.get("device", "mobile"),
        "preview_sections": preview_sections,
        "draft_has_hero_image": bool(design.draft_hero_image_id),
    })
