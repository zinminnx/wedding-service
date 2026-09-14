from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from staffing.access import PERM_PLANNER, get_wedding_for_user

from .forms import PlannerAppointmentForm, PlannerNoteForm, PlannerTaskForm, RunSheetItemForm
from .models import PlannerAppointment, PlannerNote, PlannerTask, RunSheetItem
from .services import planner_dashboard_data


def _planner_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_PLANNER)
    if wedding is None:
        raise Http404("Wedding planner workspace not available")
    return wedding


@login_required
def dashboard(request):
    wedding = _planner_wedding(request)
    context = {"wedding": wedding}
    context.update(planner_dashboard_data(wedding))
    return render(request, "planner/dashboard.html", context)


def _save_model_form(request, *, model, form_class, template_title, kind, pk=None, team=False):
    wedding = _planner_wedding(request)
    instance = None
    if pk is not None:
        instance = get_object_or_404(model, pk=pk, wedding=wedding)
    kwargs = {"instance": instance}
    if team:
        kwargs["wedding"] = wedding
    form = form_class(request.POST or None, **kwargs)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.wedding = wedding
        if hasattr(item, "created_by_id") and not item.created_by_id:
            item.created_by = request.user
        item.save()
        messages.success(request, f"{template_title} saved.")
        return redirect("planner:dashboard")
    return render(
        request,
        "planner/form.html",
        {"wedding": wedding, "form": form, "page_title": template_title, "kind": kind, "editing": instance is not None},
    )


@login_required
def task_form(request, pk=None):
    return _save_model_form(request, model=PlannerTask, form_class=PlannerTaskForm, template_title="Planner Task", kind="task", pk=pk, team=True)


@login_required
def appointment_form(request, pk=None):
    return _save_model_form(request, model=PlannerAppointment, form_class=PlannerAppointmentForm, template_title="Appointment", kind="appointment", pk=pk, team=True)


@login_required
def note_form(request, pk=None):
    return _save_model_form(request, model=PlannerNote, form_class=PlannerNoteForm, template_title="Planner Note", kind="note", pk=pk)


@login_required
def run_sheet_form(request, pk=None):
    return _save_model_form(request, model=RunSheetItem, form_class=RunSheetItemForm, template_title="Run Sheet Item", kind="run_sheet", pk=pk)


@login_required
@require_POST
def task_action(request, pk):
    wedding = _planner_wedding(request)
    item = get_object_or_404(PlannerTask, pk=pk, wedding=wedding)
    action = request.POST.get("action", "").strip()
    if action == "done":
        item.status = PlannerTask.Status.DONE
        item.save(update_fields=["status", "completed_at", "updated_at"])
        messages.success(request, f"'{item.title}' marked done.")
    elif action == "reopen":
        item.status = PlannerTask.Status.TODO
        item.save(update_fields=["status", "completed_at", "updated_at"])
        messages.success(request, f"'{item.title}' reopened.")
    elif action == "delete":
        title = item.title
        item.delete()
        messages.success(request, f"'{title}' removed.")
    else:
        return HttpResponseBadRequest("Unknown action")
    return redirect("planner:dashboard")


@login_required
@require_POST
def appointment_delete(request, pk):
    wedding = _planner_wedding(request)
    item = get_object_or_404(PlannerAppointment, pk=pk, wedding=wedding)
    title = item.title
    item.delete()
    messages.success(request, f"Appointment '{title}' removed.")
    return redirect("planner:dashboard")


@login_required
@require_POST
def note_delete(request, pk):
    wedding = _planner_wedding(request)
    item = get_object_or_404(PlannerNote, pk=pk, wedding=wedding)
    title = item.title
    item.delete()
    messages.success(request, f"Note '{title}' removed.")
    return redirect("planner:dashboard")


@login_required
@require_POST
def run_sheet_action(request, pk):
    wedding = _planner_wedding(request)
    item = get_object_or_404(RunSheetItem, pk=pk, wedding=wedding)
    action = request.POST.get("action", "").strip()
    if action == "done":
        item.status = RunSheetItem.Status.DONE
        item.save(update_fields=["status", "updated_at"])
        messages.success(request, f"'{item.title}' marked done.")
    elif action == "ready":
        item.status = RunSheetItem.Status.READY
        item.save(update_fields=["status", "updated_at"])
        messages.success(request, f"'{item.title}' marked ready.")
    elif action == "delete":
        title = item.title
        item.delete()
        messages.success(request, f"'{title}' removed from run sheet.")
    else:
        return HttpResponseBadRequest("Unknown action")
    return redirect("planner:dashboard")
