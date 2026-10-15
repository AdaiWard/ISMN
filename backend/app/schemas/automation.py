from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    trigger_key: str = Field(pattern=r"^(reachability_failure|high_latency|interface_down)$")
    action_type: str = Field(pattern=r"^(notify|retry_check|reenable_interface)$")
    mode: str = Field(default="dry_run", pattern=r"^(dry_run|manual_approval|active)$")
    device_id: int | None = None
    config_json: dict = Field(default_factory=dict)
    enabled: bool = True


class AutomationRuleRead(ORMModel):
    id: int
    name: str
    trigger_key: str
    action_type: str
    mode: str
    device_id: int | None
    config_json: dict
    enabled: bool
    created_by: int


class AutomationRunRead(ORMModel):
    id: int
    rule_id: int
    incident_id: int | None
    status: str
    dry_run: bool
    requires_approval: bool
    approved_by: int | None
    detail: str
    started_at: datetime
    finished_at: datetime | None


class PauseRequest(BaseModel):
    paused: bool

