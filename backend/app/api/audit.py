from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.db.models import AuditLog, Role, User
from app.db.session import get_db


router = APIRouter(prefix="/audit", tags=["Аудит"])


@router.get("")
def audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_roles(Role.admin.value)),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    items = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": [{"id": x.id, "actor_id": x.actor_id, "action": x.action, "object_type": x.object_type, "object_id": x.object_id, "detail": x.detail_json, "created_at": x.created_at} for x in items], "total": total, "limit": limit, "offset": offset}

