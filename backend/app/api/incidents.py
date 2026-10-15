from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_roles
from app.db.models import Incident, IncidentEvent, IncidentStatus, Role, User
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.incident import IncidentAction, IncidentEventRead, IncidentRead
from app.services.audit import write_audit


router = APIRouter(prefix="/incidents", tags=["Инциденты"])


@router.get("", response_model=Page[IncidentRead])
def list_incidents(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[IncidentRead]:
    conditions = [Incident.status == status] if status else []
    total = db.scalar(select(func.count()).select_from(Incident).where(*conditions)) or 0
    items = db.scalars(select(Incident).where(*conditions).order_by(Incident.opened_at.desc()).limit(limit).offset(offset)).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{incident_id}/events", response_model=list[IncidentEventRead])
def incident_events(incident_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(IncidentEvent).where(IncidentEvent.incident_id == incident_id).order_by(IncidentEvent.created_at)).all()


@router.post("/{incident_id}/acknowledge", response_model=IncidentRead)
def acknowledge(
    incident_id: int,
    payload: IncidentAction,
    actor: User = Depends(require_roles(Role.admin.value, Role.operator.value)),
    db: Session = Depends(get_db),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    if incident.status == IncidentStatus.resolved.value:
        raise HTTPException(status_code=409, detail="Инцидент уже закрыт")
    incident.status = IncidentStatus.acknowledged.value
    incident.acknowledged_at = datetime.now(timezone.utc)
    db.add(IncidentEvent(incident_id=incident.id, event_type="acknowledged", message=payload.note or "Инцидент принят в работу", actor_id=actor.id))
    write_audit(db, "incident.acknowledge", "incident", incident.id, actor.id)
    db.commit()
    db.refresh(incident)
    return incident

