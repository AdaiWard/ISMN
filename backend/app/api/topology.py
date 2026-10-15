from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_roles
from app.db.models import Device, NetworkLink, Role, User
from app.db.session import get_db
from app.services.audit import write_audit


class LinkCreate(BaseModel):
    source_device_id: int
    target_device_id: int
    label: str | None = Field(default=None, max_length=120)


router = APIRouter(prefix="/topology", tags=["Топология"])


@router.get("")
def topology(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    devices = db.scalars(select(Device).where(Device.archived.is_(False))).all()
    links = db.scalars(select(NetworkLink)).all()
    return {
        "is_manual": True,
        "notice": "Связи заданы вручную; LLDP/CDP autodiscovery не заявляется",
        "nodes": [{"id": d.id, "name": d.name, "status": d.status, "type": d.device_type} for d in devices],
        "links": [{"id": link.id, "source": link.source_device_id, "target": link.target_device_id, "label": link.label, "is_manual": True} for link in links],
    }


@router.post("/links", status_code=201)
def add_link(payload: LinkCreate, actor: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)):
    if payload.source_device_id == payload.target_device_id or not db.get(Device, payload.source_device_id) or not db.get(Device, payload.target_device_id):
        raise HTTPException(status_code=422, detail="Некорректные узлы связи")
    source, target = sorted((payload.source_device_id, payload.target_device_id))
    link = NetworkLink(source_device_id=source, target_device_id=target, label=payload.label, is_manual=True)
    db.add(link)
    db.flush()
    write_audit(db, "topology.link.create", "network_link", link.id, actor.id)
    db.commit()
    return {"id": link.id, "is_manual": True}

