from .models import AuditEvent


def record_event(
    *,
    wedding,
    actor=None,
    category=AuditEvent.Category.SYSTEM,
    action,
    message="",
    entity_type="",
    entity_id="",
    route_name="",
    status_code=0,
    source=AuditEvent.Source.MANUAL,
    metadata=None,
    source_fingerprint=None,
    created_at=None,
):
    if not wedding:
        return None

    actor_label = ""
    actor_role = ""
    if actor is not None:
        actor_label = (
            getattr(actor, "get_full_name", lambda: "")() or getattr(actor, "username", "") or ""
        )[:160]
        actor_role = (getattr(actor, "role", "") or "")[:40]

    defaults = {
        "wedding": wedding,
        "actor": actor if getattr(actor, "pk", None) else None,
        "actor_label": actor_label,
        "actor_role": actor_role,
        "category": category,
        "action": (action or "event")[:128],
        "entity_type": (entity_type or "")[:80],
        "entity_id": (str(entity_id) if entity_id is not None else "")[:80],
        "message": (message or "")[:500],
        "route_name": (route_name or "")[:160],
        "status_code": int(status_code or 0),
        "source": source,
        "metadata": metadata or {},
    }
    if created_at is not None:
        defaults["created_at"] = created_at

    if source_fingerprint:
        event, _ = AuditEvent.objects.get_or_create(
            source_fingerprint=source_fingerprint,
            defaults=defaults,
        )
        return event
    return AuditEvent.objects.create(**defaults)
