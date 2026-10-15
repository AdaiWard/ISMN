from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class IncidentRead(ORMModel):
    id: int
    device_id: int
    rule_key: str
    severity: str
    status: str
    title: str
    explanation: str
    opened_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class IncidentAction(BaseModel):
    note: str | None = None


class IncidentEventRead(ORMModel):
    id: int
    incident_id: int
    event_type: str
    message: str
    actor_id: int | None
    created_at: datetime

