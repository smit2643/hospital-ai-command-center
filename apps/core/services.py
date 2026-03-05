from typing import Any
from .models import AuditLog


def log_audit(*, actor, action: str, object_type: str, object_id: str, metadata: dict[str, Any] | None = None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        metadata=metadata or {},
    )
