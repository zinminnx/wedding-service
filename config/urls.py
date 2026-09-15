from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("health/", include("security_hardening.urls")),
    path("", include("audit_analytics.urls")),
    path("", include("dashboard_themes.urls")),
    path("", include("archive_restore.urls")),
    path("", include("printing.urls")),
    path("", include("integrations.urls")),
    path("", include("financial_docs.urls")),
    path("", include("vendors.urls")),
    path("", include("planner.urls")),
    path("", include("budgeting.urls")),
    path("", include("transportation.urls")),
    path("", include("event_tools.urls")),
    path("", include("photos.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("weddings.urls")),
    path("dashboard/modules/", include("modules.urls")),
    path("dashboard/design/", include("invitation_themes.urls")),
    path("dashboard/guests/", include("guests.urls")),
    path("dashboard/rsvp/", include("rsvp.urls")),
    path("dashboard/gifts/", include("gifts.urls")),
    path("dashboard/staff/", include("staffing.urls")),
    path("", include("checkins.urls")),
    path("", include("invitations.urls")),
]

if settings.DEBUG and getattr(settings, "MEDIA_URL", ""):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
