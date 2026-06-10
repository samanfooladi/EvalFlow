from .middleware import get_current_request
from .models import AuditLog


def _client_ip(request) -> str | None:
    # Behind nginx the first X-Forwarded-For hop is the client.
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_event(
    request=None,
    *,
    action: str,
    model: str = "",
    object_id: str = "",
    object_repr: str = "",
    changes: dict | None = None,
    actor=None,
) -> AuditLog:
    request = request or get_current_request()
    ip = None
    user_agent = ""
    if request is not None:
        ip = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]
        if actor is None:
            user = getattr(request, "user", None)
            if user is not None and user.is_authenticated:
                actor = user
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        model=model,
        object_id=str(object_id),
        object_repr=object_repr[:256],
        changes=changes,
        ip=ip,
        user_agent=user_agent,
    )
