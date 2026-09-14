from django.urls import path

from . import views

app_name = "financial_docs"

urlpatterns = [
    path("dashboard/finance-docs/", views.dashboard, name="dashboard"),
    path("dashboard/finance-docs/<int:document_id>/download/", views.download, name="download"),
    path("dashboard/finance-docs/<int:document_id>/delete/", views.delete, name="delete"),
]
