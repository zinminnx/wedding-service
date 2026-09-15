from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from photos.storage_backend import photo_content_type, read_photo_bytes
from staffing.access import PERM_MANAGE_WEDDING, PERM_PRINT, get_wedding_for_user, has_wedding_permission

from .forms import PrintJobForm, WeddingPrintSettingsForm
from .models import PrintAgentDevice, PrintJob, WeddingPrintSettings
from .services import InvalidPrintTransition, transition_job


def _print_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_PRINT)
    if not wedding:
        raise Http404("Wedding not found")
    return wedding


def _job_for_user(request, public_id):
    wedding = _print_wedding(request)
    return get_object_or_404(
        PrintJob.objects.select_related("photo", "photo__guest", "requested_by"),
        wedding=wedding,
        public_id=public_id,
    )


@login_required
def dashboard(request):
    wedding = _print_wedding(request)
    settings_obj, _ = WeddingPrintSettings.objects.get_or_create(wedding=wedding)
    jobs = PrintJob.objects.filter(wedding=wedding).select_related("photo", "photo__guest", "requested_by")
    status = (request.GET.get("status") or "").strip().upper()
    if status in PrintJob.Status.values:
        jobs = jobs.filter(status=status)

    counts = dict(
        PrintJob.objects.filter(wedding=wedding)
        .values_list("status")
        .annotate(total=Count("id"))
    )
    form = PrintJobForm(
        wedding=wedding,
        initial={
            "copies": settings_obj.default_copies,
            "paper_size": settings_obj.default_paper_size,
            "fit_mode": PrintJob.FitMode.FIT,
        },
    )
    settings_form = WeddingPrintSettingsForm(instance=settings_obj)
    can_manage_settings = has_wedding_permission(request.user, wedding, PERM_MANAGE_WEDDING)
    agent_devices = PrintAgentDevice.objects.filter(wedding=wedding).order_by("name") if can_manage_settings else []

    return render(
        request,
        "printing/dashboard.html",
        {
            "wedding": wedding,
            "settings_obj": settings_obj,
            "jobs": jobs[:300],
            "form": form,
            "settings_form": settings_form,
            "status_filter": status,
            "status_choices": PrintJob.Status.choices,
            "counts": {
                "queued": counts.get(PrintJob.Status.QUEUED, 0),
                "active": counts.get(PrintJob.Status.CLAIMED, 0) + counts.get(PrintJob.Status.PRINTING, 0),
                "printed": counts.get(PrintJob.Status.PRINTED, 0),
                "failed": counts.get(PrintJob.Status.FAILED, 0),
            },
            "can_manage_settings": can_manage_settings,
            "agent_devices": agent_devices,
        },
    )


@login_required
def create_job(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _print_wedding(request)
    settings_obj, _ = WeddingPrintSettings.objects.get_or_create(wedding=wedding)
    if not settings_obj.queue_enabled:
        messages.error(request, "Printing queue is disabled for this wedding.")
        return redirect("printing:dashboard")
    if settings_obj.queue_paused:
        messages.error(request, "Printing queue is paused. Resume it before adding jobs.")
        return redirect("printing:dashboard")

    form = PrintJobForm(request.POST, wedding=wedding)
    if not form.is_valid():
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect("printing:dashboard")
    job = form.save(commit=False)
    job.requested_by = request.user
    job.save()
    messages.success(request, f"{job.public_id} added to the print queue.")
    return redirect("printing:dashboard")


@login_required
def job_action(request, public_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    job = _job_for_user(request, public_id)
    action = (request.POST.get("action") or "").strip().lower()
    try:
        transition_job(job, action)
    except InvalidPrintTransition as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"{job.public_id} updated.")
    return redirect("printing:dashboard")


@login_required
def job_source(request, public_id):
    job = _job_for_user(request, public_id)
    if not job.photo_id:
        raise Http404("This print job no longer has a source photo.")
    try:
        content = read_photo_bytes(job.photo)
    except Exception as exc:
        raise Http404("Print source file is unavailable.") from exc
    filename = job.photo.original_filename or f"{job.photo.public_id}.jpg"
    response = FileResponse(
        BytesIO(content),
        as_attachment=True,
        filename=filename,
        content_type=photo_content_type(job.photo),
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def update_settings(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _print_wedding(request)
    if not has_wedding_permission(request.user, wedding, PERM_MANAGE_WEDDING):
        raise Http404("Wedding not found")
    settings_obj, _ = WeddingPrintSettings.objects.get_or_create(wedding=wedding)
    form = WeddingPrintSettingsForm(request.POST, instance=settings_obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Printing settings saved.")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    return redirect("printing:dashboard")
