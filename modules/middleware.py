from django.contrib import messages
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from .services import module_available


NAMESPACE_MODULES = {
    "rsvp": "rsvp",
    "checkins": "checkins",
    "photos": "photos",
    "staffing": "staffing",
    "transportation": "transportation",
    "budgeting": "budgeting",
    "financial_docs": "budgeting",
    "planner": "planner",
    "vendors": "vendors",
    "invitation_themes": "invitation_themes",
}


class ModuleGateMiddleware(MiddlewareMixin):
    """Server-side feature gate for existing optional dashboard modules."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = getattr(request, "resolver_match", None)
        if not match:
            return None
        if request.path.startswith("/admin/") or match.namespace == "modules":
            return None

        module_key = self._module_key(match)
        if not module_key:
            return None

        if getattr(request.user, "is_authenticated", False):
            try:
                from staffing.access import get_wedding_for_user
                wedding = get_wedding_for_user(request.user)
            except Exception:
                wedding = None
            if not wedding:
                return None
            if not module_available(module_key, user=request.user, wedding=wedding, check_role=True):
                messages.warning(request, "This feature is not available for the selected wedding.")
                return redirect("weddings:dashboard")
            return None

        # Public photo routes are also protected when the Photos module is off.
        if module_key == "photos":
            wedding = self._public_photo_wedding(match)
            if wedding and not module_available("photos", wedding=wedding, check_role=False):
                return HttpResponseNotFound("Photo sharing is not available for this wedding.")
        return None

    def _module_key(self, match):
        if match.namespace == "gifts":
            return "return_gifts" if match.url_name == "inventory" else "gifts"
        return NAMESPACE_MODULES.get(match.namespace)

    def _public_photo_wedding(self, match):
        token = match.kwargs.get("token") if match.kwargs else None
        if not token:
            return None
        try:
            if match.url_name in {"guest_upload", "guest_download"}:
                from invitations.models import Invitation
                invitation = Invitation.objects.select_related("wedding").filter(token=token).first()
                return invitation.wedding if invitation else None
            if match.url_name in {"slideshow", "slideshow_feed"}:
                from photos.models import WeddingPhotoSettings
                settings_obj = WeddingPhotoSettings.objects.select_related("wedding").filter(slideshow_token=token).first()
                return settings_obj.wedding if settings_obj else None
        except Exception:
            return None
        return None
