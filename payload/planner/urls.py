from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("dashboard/planner/", views.dashboard, name="dashboard"),
    path("dashboard/planner/tasks/new/", views.task_form, name="task_add"),
    path("dashboard/planner/tasks/<int:pk>/edit/", views.task_form, name="task_edit"),
    path("dashboard/planner/tasks/<int:pk>/action/", views.task_action, name="task_action"),
    path("dashboard/planner/appointments/new/", views.appointment_form, name="appointment_add"),
    path("dashboard/planner/appointments/<int:pk>/edit/", views.appointment_form, name="appointment_edit"),
    path("dashboard/planner/appointments/<int:pk>/delete/", views.appointment_delete, name="appointment_delete"),
    path("dashboard/planner/notes/new/", views.note_form, name="note_add"),
    path("dashboard/planner/notes/<int:pk>/edit/", views.note_form, name="note_edit"),
    path("dashboard/planner/notes/<int:pk>/delete/", views.note_delete, name="note_delete"),
    path("dashboard/planner/run-sheet/new/", views.run_sheet_form, name="run_sheet_add"),
    path("dashboard/planner/run-sheet/<int:pk>/edit/", views.run_sheet_form, name="run_sheet_edit"),
    path("dashboard/planner/run-sheet/<int:pk>/action/", views.run_sheet_action, name="run_sheet_action"),
]
