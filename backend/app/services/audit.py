from sqlalchemy.orm import Session

from app.db.models import AuditLog


def write_audit(
    db: Session,
    action: str,
    object_type: str,
    object_id: int | str | None,
    actor_id: int | None,
    detail: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        detail_json=detail or {},
    )
    db.add(entry)
    return entry

