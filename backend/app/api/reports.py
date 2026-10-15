from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import Device, Incident, MonitoringCheck, User
from app.db.session import get_db


router = APIRouter(prefix="/reports", tags=["Отчёты"])


def availability_rows(db: Session, hours: int) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = db.execute(
        select(
            Device.id,
            Device.name,
            Device.address,
            func.count(MonitoringCheck.id),
            func.sum(case((MonitoringCheck.success.is_(True), 1), else_=0)),
            func.avg(MonitoringCheck.latency_ms),
        )
        .outerjoin(MonitoringCheck, (MonitoringCheck.device_id == Device.id) & (MonitoringCheck.observed_at >= since))
        .where(Device.archived.is_(False))
        .group_by(Device.id)
        .order_by(Device.name)
    ).all()
    rows = []
    for device_id, name, address, total, successful, latency in results:
        successful = successful or 0
        rows.append(
            {
                "device_id": device_id,
                "name": name,
                "address": address,
                "checks": total,
                "successful_checks": successful,
                "observed_availability_percent": round(successful * 100 / total, 2) if total else None,
                "average_latency_ms": round(latency, 2) if latency is not None else None,
                "period_hours": hours,
            }
        )
    return rows


@router.get("/availability")
def availability(hours: int = Query(24, ge=1, le=24 * 365), _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": availability_rows(db, hours), "generated_at": datetime.now(timezone.utc), "note": "Доступность вычислена только для фактически наблюдаемого периода"}


@router.get("/availability.csv")
def availability_csv(hours: int = Query(24, ge=1, le=24 * 365), _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = availability_rows(db, hours)
    output = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["device_id", "name", "address", "checks", "successful_checks", "observed_availability_percent", "average_latency_ms", "period_hours"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=ismn_availability.csv"})

