from django.utils import timezone

from .models import PlannerAppointment, PlannerNote, PlannerTask, RunSheetItem


def planner_dashboard_data(wedding):
    now = timezone.now()
    tasks = PlannerTask.objects.filter(wedding=wedding).select_related("assigned_to")
    open_tasks = tasks.exclude(status__in=[PlannerTask.Status.DONE, PlannerTask.Status.CANCELLED])
    upcoming_tasks = open_tasks.filter(due_at__isnull=False).order_by("due_at")[:8]
    overdue = open_tasks.filter(due_at__lt=now).count()
    completed = tasks.filter(status=PlannerTask.Status.DONE).count()

    appointments = (
        PlannerAppointment.objects.filter(wedding=wedding, starts_at__gte=now)
        .select_related("assigned_to")
        .order_by("starts_at")[:6]
    )
    run_sheet = RunSheetItem.objects.filter(wedding=wedding).order_by("scheduled_at", "sort_order")[:12]
    notes = PlannerNote.objects.filter(wedding=wedding).select_related("created_by")[:6]

    reminders = []
    for task in open_tasks.filter(reminder_at__isnull=False).order_by("reminder_at")[:10]:
        reminders.append({"at": task.reminder_at, "type": "Task", "title": task.title})
    for item in PlannerAppointment.objects.filter(wedding=wedding, reminder_at__isnull=False, starts_at__gte=now).order_by("reminder_at")[:10]:
        reminders.append({"at": item.reminder_at, "type": "Appointment", "title": item.title})
    reminders.sort(key=lambda row: row["at"])
    reminders = reminders[:8]

    return {
        "task_total": tasks.count(),
        "task_open": open_tasks.count(),
        "task_overdue": overdue,
        "task_completed": completed,
        "upcoming_tasks": upcoming_tasks,
        "appointments": appointments,
        "run_sheet": run_sheet,
        "notes": notes,
        "reminders": reminders,
    }
