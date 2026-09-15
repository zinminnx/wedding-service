from .models import AuditEvent
from .services import record_event


AUDITED_NAMESPACES = {
    "weddings": AuditEvent.Category.WEDDING,
    "modules": AuditEvent.Category.MODULE,
    "staffing": AuditEvent.Category.ACCESS,
    "guests": AuditEvent.Category.GUESTS,
    "invitations": AuditEvent.Category.INVITATIONS,
    "rsvp": AuditEvent.Category.RSVP,
    "gifts": AuditEvent.Category.GIFTS,
    "checkins": AuditEvent.Category.CHECKIN,
    "photos": AuditEvent.Category.PHOTOS,
    "printing": AuditEvent.Category.PRINTING,
    "planner": AuditEvent.Category.PLANNER,
    "vendors": AuditEvent.Category.PLANNER,
    "budgeting": AuditEvent.Category.FINANCE,
    "financial_docs": AuditEvent.Category.FINANCE,
    "integrations": AuditEvent.Category.STORAGE,
    "archive_restore": AuditEvent.Category.ARCHIVE,
    "invitation_themes": AuditEvent.Category.THEME,
    "dashboard_themes": AuditEvent.Category.THEME,
    "transportation": AuditEvent.Category.WEDDING,
}


class AuditTrailMiddleware:
    """Record successful authenticated mutations without storing POST bodies, tokens or IPs."""

    mutation_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._record(request, response)
        except Exception:
            # Audit logging must never make a wedding operation fail.
            pass
        return response

    def _record(self, request, response):
        if request.method.upper() not in self.mutation_methods:
            return
        if getattr(response, "status_code", 500) >= 400:
            return
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return

        match = getattr(request, "resolver_match", None)
        namespace = getattr(match, "namespace", "") if match else ""
        if namespace not in AUDITED_NAMESPACES:
            return

        from staffing.access import get_user_wedding_role, get_wedding_for_user

        wedding = get_wedding_for_user(user)
        if not wedding:
            return

        url_name = getattr(match, "url_name", "") or "mutation"
        route_name = f"{namespace}:{url_name}"
        entity_id = ""
        kwargs = getattr(match, "kwargs", {}) or {}
        # Never persist invitation/agent/source tokens. Public IDs and numeric IDs are enough.
        safe_keys = (
            "public_id",
            "pk",
            "id",
            "job_id",
            "quote_id",
            "vendor_id",
            "membership_id",
            "snapshot_id",
            "theme_id",
        )
        for key in safe_keys:
            value = kwargs.get(key)
            if value not in (None, ""):
                entity_id = str(value)[:80]
                break

        action = route_name.replace(":", ".")
        role = get_user_wedding_role(user, wedding) or getattr(user, "role", "") or ""
        event = record_event(
            wedding=wedding,
            actor=user,
            category=AUDITED_NAMESPACES[namespace],
            action=action,
            entity_type=namespace,
            entity_id=entity_id,
            route_name=route_name,
            status_code=getattr(response, "status_code", 0),
            source=AuditEvent.Source.MIDDLEWARE,
            message=f"{route_name} completed via {request.method.upper()}.",
            metadata={"method": request.method.upper(), "role": role},
        )
        return event
