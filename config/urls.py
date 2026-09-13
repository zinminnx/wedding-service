from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("photos.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("weddings.urls")),
    path("dashboard/guests/", include("guests.urls")),
    path("dashboard/rsvp/", include("rsvp.urls")),
    path("dashboard/gifts/", include("gifts.urls")),
    path("dashboard/staff/", include("staffing.urls")),
    path("", include("checkins.urls")),
    path("", include("invitations.urls")),
]

if settings.DEBUG and getattr(settings, "MEDIA_URL", ""):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
