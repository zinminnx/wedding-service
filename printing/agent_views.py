from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from staffing.access import PERM_MANAGE_WEDDING, get_wedding_for_user

from .models import PrintAgentDevice


def _management_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if not wedding:
        raise Http404("Wedding not found")
    return wedding


@login_required
def create_device(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _management_wedding(request)
    name = (request.POST.get("name") or "Venue Print PC").strip()[:120] or "Venue Print PC"
    printer_name = (request.POST.get("printer_name") or "").strip()[:200]
    device, raw_token = PrintAgentDevice.issue_token(
        wedding=wedding,
        name=name,
        printer_name=printer_name,
        created_by=request.user,
    )
    request.session[f"print_agent_secret_{device.pk}"] = raw_token
    return redirect("printing:agent_secret", pk=device.pk)


@login_required
def device_secret(request, pk):
    wedding = _management_wedding(request)
    device = get_object_or_404(PrintAgentDevice, pk=pk, wedding=wedding)
    key = f"print_agent_secret_{device.pk}"
    raw_token = request.session.pop(key, None)
    return render(
        request,
        "printing/agent_secret.html",
        {"wedding": wedding, "device": device, "raw_token": raw_token},
    )


@login_required
def device_action(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = _management_wedding(request)
    device = get_object_or_404(PrintAgentDevice, pk=pk, wedding=wedding)
    action = (request.POST.get("action") or "").strip().lower()
    if action == "revoke":
        device.enabled = False
        device.save(update_fields=["enabled", "updated_at"])
        messages.success(request, f"{device.name} was revoked.")
    elif action == "enable":
        device.enabled = True
        device.save(update_fields=["enabled", "updated_at"])
        messages.success(request, f"{device.name} was enabled.")
    elif action == "rotate":
        raw_token = device.rotate_token()
        request.session[f"print_agent_secret_{device.pk}"] = raw_token
        messages.success(request, f"{device.name} token rotated. The old token no longer works.")
        return redirect("printing:agent_secret", pk=device.pk)
    else:
        return HttpResponseBadRequest("Unknown device action")
    return redirect("printing:dashboard")
