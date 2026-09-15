from django.urls import path

from . import agent_api, agent_views, views

app_name = "printing"

urlpatterns = [
    path("dashboard/printing/agents/new/", agent_views.create_device, name="agent_create"),
    path("dashboard/printing/agents/<int:pk>/secret/", agent_views.device_secret, name="agent_secret"),
    path("dashboard/printing/agents/<int:pk>/action/", agent_views.device_action, name="agent_action"),
    path("api/printing/agent/heartbeat/", agent_api.heartbeat, name="agent_heartbeat"),
    path("api/printing/agent/poll/", agent_api.poll, name="agent_poll"),
    path("api/printing/agent/jobs/<str:public_id>/source/", agent_api.job_source, name="agent_job_source"),
    path("api/printing/agent/jobs/<str:public_id>/state/", agent_api.job_state, name="agent_job_state"),
    path("dashboard/printing/", views.dashboard, name="dashboard"),
    path("dashboard/printing/jobs/new/", views.create_job, name="create_job"),
    path("dashboard/printing/jobs/<str:public_id>/action/", views.job_action, name="job_action"),
    path("dashboard/printing/jobs/<str:public_id>/source/", views.job_source, name="job_source"),
    path("dashboard/printing/settings/", views.update_settings, name="settings"),
]
