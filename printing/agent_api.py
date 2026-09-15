import json
from datetime import timedelta
from io import BytesIO

from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from modules.services import module_available
from photos.storage_backend import photo_content_type, read_photo_bytes

from .agent_auth import authenticate_agent
from .models import PrintAgentDevice, PrintJob, WeddingPrintSettings

CLAIM_LEASE_SECONDS = 300


def _json_body(request):
    try:
        raw = request.body.decode("utf-8") if request.body else "{}"
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _unauthorized():
    return JsonResponse({"ok": False, "error": "Invalid or disabled print-agent token."}, status=401)


def _forbidden(message):
    return JsonResponse({"ok": False, "error": message}, status=403)


def _authenticate(request):
    device = authenticate_agent(request)
    if not device:
        return None, _unauthorized()
    if not module_available("printing", wedding=device.wedding, check_role=False):
        return None, _forbidden("Printing is not available for this wedding.")
    return device, None


def _device_label(device):
    bits = [device.name]
    if device.hostname:
        bits.append(device.hostname)
    return " @ ".join(bits)[:120]


def _job_payload(request, job):
    photo = job.photo
    return {
        "id": job.public_id,
        "status": job.status,
        "copies": job.copies,
        "paper_size": job.paper_size,
        "fit_mode": job.fit_mode,
        "notes": job.notes,
        "source_url": request.build_absolute_uri(reverse("printing:agent_job_source", args=[job.public_id])),
        "source_filename": (photo.original_filename if photo else "") or f"{job.public_id}.jpg",
        "source_content_type": photo_content_type(photo) if photo else "application/octet-stream",
        "photo_id": photo.public_id if photo else None,
        "created_at": job.created_at.isoformat(),
    }


@csrf_exempt
@require_POST
def heartbeat(request):
    device, error = _authenticate(request)
    if error:
        return error
    payload = _json_body(request)
    fields = {"last_seen_at": timezone.now(), "last_error": ""}
    hostname = str(payload.get("hostname") or "").strip()[:120]
    printer_name = str(payload.get("printer_name") or "").strip()[:200]
    version = str(payload.get("version") or "").strip()[:40]
    if hostname:
        fields["hostname"] = hostname
    if printer_name:
        fields["printer_name"] = printer_name
    if version:
        fields["agent_version"] = version
    PrintAgentDevice.objects.filter(pk=device.pk).update(**fields)
    return JsonResponse({"ok": True, "server_time": timezone.now().isoformat()})


@csrf_exempt
@require_POST
def poll(request):
    device, error = _authenticate(request)
    if error:
        return error

    payload = _json_body(request)
    update_fields = {"last_seen_at": timezone.now(), "last_error": ""}
    for source, target, limit in [
        ("hostname", "hostname", 120),
        ("printer_name", "printer_name", 200),
        ("version", "agent_version", 40),
    ]:
        value = str(payload.get(source) or "").strip()[:limit]
        if value:
            update_fields[target] = value
    PrintAgentDevice.objects.filter(pk=device.pk).update(**update_fields)
    device.refresh_from_db(fields=["hostname", "printer_name", "agent_version", "last_seen_at", "last_error"])

    settings_obj, _ = WeddingPrintSettings.objects.get_or_create(wedding=device.wedding)
    if not settings_obj.queue_enabled:
        return JsonResponse({"ok": True, "queue": "disabled", "job": None})
    if settings_obj.queue_paused:
        return JsonResponse({"ok": True, "queue": "paused", "job": None})

    now = timezone.now()
    lease_until = now + timedelta(seconds=CLAIM_LEASE_SECONDS)

    with transaction.atomic():
        # A job that was only claimed, but never started printing, is safe to make
        # available again after its lease expires. PRINTING jobs are never auto-
        # requeued because doing so could create a duplicate physical print.
        PrintJob.objects.filter(
            wedding=device.wedding,
            status=PrintJob.Status.CLAIMED,
            claim_expires_at__lt=now,
        ).update(
            status=PrintJob.Status.QUEUED,
            agent_device=None,
            claimed_by_label="",
            claimed_at=None,
            claim_expires_at=None,
        )

        job = (
            PrintJob.objects.select_for_update(skip_locked=True)
            .select_related("photo")
            .filter(
                wedding=device.wedding,
                status=PrintJob.Status.QUEUED,
                photo__isnull=False,
            )
            .order_by("created_at", "id")
            .first()
        )
        if not job:
            return JsonResponse({"ok": True, "queue": "ready", "job": None})

        job.status = PrintJob.Status.CLAIMED
        job.agent_device = device
        job.claimed_by_label = _device_label(device)
        job.claimed_at = now
        job.claim_expires_at = lease_until
        job.error_message = ""
        job.save(update_fields=[
            "status", "agent_device", "claimed_by_label", "claimed_at",
            "claim_expires_at", "error_message", "updated_at",
        ])

    return JsonResponse({"ok": True, "queue": "ready", "job": _job_payload(request, job)})


@csrf_exempt
@require_GET
def job_source(request, public_id):
    device, error = _authenticate(request)
    if error:
        return error
    job = (
        PrintJob.objects.select_related("photo")
        .filter(wedding=device.wedding, public_id=public_id, agent_device=device)
        .first()
    )
    if not job or job.status not in {PrintJob.Status.CLAIMED, PrintJob.Status.PRINTING}:
        return JsonResponse({"ok": False, "error": "Print job is not assigned to this agent."}, status=404)
    if not job.photo_id:
        return JsonResponse({"ok": False, "error": "Print source is unavailable."}, status=404)

    if job.status == PrintJob.Status.CLAIMED:
        PrintJob.objects.filter(pk=job.pk).update(
            claim_expires_at=timezone.now() + timedelta(seconds=CLAIM_LEASE_SECONDS)
        )
    try:
        content = read_photo_bytes(job.photo)
    except Exception as exc:
        PrintAgentDevice.objects.filter(pk=device.pk).update(last_error=str(exc)[:500])
        return JsonResponse({"ok": False, "error": "Print source is unavailable."}, status=404)

    response = FileResponse(
        BytesIO(content),
        as_attachment=True,
        filename=job.photo.original_filename or f"{job.photo.public_id}.jpg",
        content_type=photo_content_type(job.photo),
    )
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@csrf_exempt
@require_POST
def job_state(request, public_id):
    device, error = _authenticate(request)
    if error:
        return error
    payload = _json_body(request)
    state = str(payload.get("state") or "").strip().lower()
    detail = str(payload.get("error") or "").strip()[:500]
    now = timezone.now()

    with transaction.atomic():
        job = (
            PrintJob.objects.select_for_update()
            .filter(wedding=device.wedding, public_id=public_id, agent_device=device)
            .first()
        )
        if not job:
            return JsonResponse({"ok": False, "error": "Print job is not assigned to this agent."}, status=404)

        if state == "printing":
            if job.status != PrintJob.Status.CLAIMED:
                return JsonResponse({"ok": False, "error": "Only a claimed job can start printing."}, status=409)
            job.status = PrintJob.Status.PRINTING
            job.printing_started_at = now
            job.claim_expires_at = None
            job.error_message = ""
        elif state == "printed":
            if job.status not in {PrintJob.Status.CLAIMED, PrintJob.Status.PRINTING}:
                return JsonResponse({"ok": False, "error": "Job is not active."}, status=409)
            job.status = PrintJob.Status.PRINTED
            if not job.printing_started_at:
                job.printing_started_at = now
            job.completed_at = now
            job.claim_expires_at = None
            job.error_message = ""
        elif state == "failed":
            if job.status not in {PrintJob.Status.CLAIMED, PrintJob.Status.PRINTING}:
                return JsonResponse({"ok": False, "error": "Job is not active."}, status=409)
            job.status = PrintJob.Status.FAILED
            job.completed_at = now
            job.claim_expires_at = None
            job.error_message = detail or "Local Print Agent reported a printing failure."
            PrintAgentDevice.objects.filter(pk=device.pk).update(last_error=job.error_message)
        else:
            return JsonResponse({"ok": False, "error": "Unknown state."}, status=400)

        job.save(update_fields=[
            "status", "printing_started_at", "completed_at",
            "claim_expires_at", "error_message", "updated_at",
        ])

    return JsonResponse({"ok": True, "job": job.public_id, "status": job.status})
