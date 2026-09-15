from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from integrations.storage import read_stored_object
from staffing.access import get_wedding_for_user

from .models import ArchiveEvent, ArchiveSnapshot
from .services import (
    ArchiveError,
    build_snapshot,
    mark_delete_pending as service_mark_delete_pending,
    mark_wedding_archived,
    restore_existing_workspace,
    verify_snapshot,
)


def _owner_wedding(request):
    wedding = get_wedding_for_user(request.user)
    if not wedding:
        raise Http404("Wedding not found")
    if not request.user.is_superuser and wedding.owner_id != request.user.id:
        raise Http404("Wedding not found")
    return wedding


def _snapshot_for_owner(request, public_id):
    wedding = _owner_wedding(request)
    return wedding, get_object_or_404(
        ArchiveSnapshot.objects.select_related("stored_object", "wedding"),
        wedding=wedding,
        public_id=public_id,
    )


@login_required
def dashboard(request):
    wedding = _owner_wedding(request)
    snapshots = ArchiveSnapshot.objects.filter(wedding=wedding).select_related("stored_object", "created_by")[:50]
    events = ArchiveEvent.objects.filter(wedding_public_id=wedding.public_id).select_related("actor", "snapshot")[:30]
    latest_verified = ArchiveSnapshot.objects.filter(
        wedding=wedding,
        verified_at__isnull=False,
        status__in=[ArchiveSnapshot.Status.READY, ArchiveSnapshot.Status.RESTORED],
    ).first()
    return render(request, "archive_restore/dashboard.html", {
        "wedding": wedding,
        "snapshots": snapshots,
        "events": events,
        "latest_verified": latest_verified,
    })


@login_required
def create_snapshot(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _owner_wedding(request)
    try:
        snapshot = build_snapshot(wedding=wedding, actor=request.user)
        messages.success(request, f"Archive {snapshot.public_id} created and verified.")
    except Exception as exc:
        messages.error(request, f"Archive export failed: {exc}")
    return redirect("archive_restore:dashboard")


@login_required
def verify_snapshot_view(request, public_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    _, snapshot = _snapshot_for_owner(request, public_id)
    try:
        verify_snapshot(snapshot, actor=request.user)
        messages.success(request, f"{snapshot.public_id} passed checksum verification.")
    except Exception as exc:
        messages.error(request, f"Verification failed: {exc}")
    return redirect("archive_restore:dashboard")


@login_required
def download_snapshot(request, public_id):
    _, snapshot = _snapshot_for_owner(request, public_id)
    if not snapshot.stored_object_id:
        raise Http404("Archive file not found")
    try:
        content = read_stored_object(snapshot.stored_object)
    except Exception as exc:
        raise Http404("Archive file is unavailable") from exc
    ArchiveEvent.objects.create(
        snapshot=snapshot,
        wedding_public_id=snapshot.wedding_public_id,
        actor=request.user,
        action=ArchiveEvent.Action.DOWNLOADED,
        message="Owner downloaded the archive package.",
    )
    filename = f"{snapshot.wedding_public_id}-{snapshot.public_id}.zip"
    return FileResponse(BytesIO(content), as_attachment=True, filename=filename, content_type="application/zip")


@login_required
def archive_wedding(request, public_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    _, snapshot = _snapshot_for_owner(request, public_id)
    try:
        mark_wedding_archived(snapshot, actor=request.user)
        messages.success(request, "Wedding archived. The verified export and database rows were retained.")
    except ArchiveError as exc:
        messages.error(request, str(exc))
    return redirect("archive_restore:dashboard")


@login_required
def restore_wedding(request, public_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    _, snapshot = _snapshot_for_owner(request, public_id)
    try:
        restore_existing_workspace(snapshot, actor=request.user)
        messages.success(request, "Wedding restored to Draft. Review settings before publishing again.")
    except Exception as exc:
        messages.error(request, f"Restore failed: {exc}")
    return redirect("archive_restore:dashboard")


@login_required
def mark_delete_pending(request, public_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    _, snapshot = _snapshot_for_owner(request, public_id)
    confirmation = (request.POST.get("confirm") or "").strip()
    if confirmation != snapshot.wedding_public_id:
        messages.error(request, f"Type {snapshot.wedding_public_id} to confirm Delete Pending.")
        return redirect("archive_restore:dashboard")
    try:
        service_mark_delete_pending(snapshot, actor=request.user)
        messages.warning(request, "Wedding marked Delete Pending. No data was purged by v13.0.")
    except ArchiveError as exc:
        messages.error(request, str(exc))
    return redirect("archive_restore:dashboard")
