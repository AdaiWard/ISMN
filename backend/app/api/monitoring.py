from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import Device, Incident, IncidentStatus, MetricSample, MonitoringCheck, User
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.device import CheckRead, MetricRead


router = APIRouter(tags=["Мониторинг"])


@router.get("/dashboard")
def dashboard(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(Device.status, func.count(Device.id)).where(Device.archived.is_(False)).group_by(Device.status)
    ).all()
    counts = {status: count for status, count in rows}
    active_incidents = db.scalar(select(func.count()).select_from(Incident).where(Incident.status != IncidentStatus.resolved.value)) or 0
    return {
        "total_devices": sum(counts.values()),
        "status_counts": {key: counts.get(key, 0) for key in ("online", "offline", "degraded", "unknown", "maintenance")},
        "active_incidents": active_incidents,
        "generated_at": datetime.now(timezone.utc),
        "data_source": "server_database",
    }


@router.get("/devices/{device_id}/checks", response_model=Page[CheckRead])
def checks(
    device_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[CheckRead]:
    total = db.scalar(select(func.count()).select_from(MonitoringCheck).where(MonitoringCheck.device_id == device_id)) or 0
    items = db.scalars(select(MonitoringCheck).where(MonitoringCheck.device_id == device_id).order_by(MonitoringCheck.observed_at.desc()).limit(limit).offset(offset)).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/devices/{device_id}/metrics", response_model=list[MetricRead])
def metrics(
    device_id: int,
    name: str | None = None,
    hours: int = Query(24, ge=1, le=24 * 90),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MetricSample]:
    conditions = [MetricSample.device_id == device_id, MetricSample.observed_at >= datetime.now(timezone.utc) - timedelta(hours=hours)]
    if name:
        conditions.append(MetricSample.name == name)
    return list(db.scalars(select(MetricSample).where(*conditions).order_by(MetricSample.observed_at)).all())

