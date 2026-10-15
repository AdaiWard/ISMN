from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


DEVICE_TYPES = {"router", "switch", "server", "pc", "printer", "access_point", "other"}
MONITORING_PROFILES = {"icmp", "icmp_snmp", "test_agent"}


class DeviceBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=1, max_length=253)
    device_type: str = "other"
    vendor: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=160)
    group_id: int | None = None
    credential_id: int | None = None
    enabled: bool = True
    monitoring_profile: str = "icmp"
    check_interval: int = Field(default=30, ge=10, le=86400)
    automation_allowed: bool = False

    @field_validator("device_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in DEVICE_TYPES:
            raise ValueError("Unsupported device type")
        return value

    @field_validator("monitoring_profile")
    @classmethod
    def valid_profile(cls, value: str) -> str:
        if value not in MONITORING_PROFILES:
            raise ValueError("Unsupported monitoring profile")
        return value


class DeviceCreate(DeviceBase):
    is_simulated: bool = False


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    address: str | None = Field(default=None, min_length=1, max_length=253)
    device_type: str | None = None
    vendor: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=160)
    group_id: int | None = None
    credential_id: int | None = None
    enabled: bool | None = None
    monitoring_profile: str | None = None
    check_interval: int | None = Field(default=None, ge=10, le=86400)
    automation_allowed: bool | None = None

    @field_validator("device_type")
    @classmethod
    def valid_optional_type(cls, value: str | None) -> str | None:
        if value is not None and value not in DEVICE_TYPES:
            raise ValueError("Unsupported device type")
        return value

    @field_validator("monitoring_profile")
    @classmethod
    def valid_optional_profile(cls, value: str | None) -> str | None:
        if value is not None and value not in MONITORING_PROFILES:
            raise ValueError("Unsupported monitoring profile")
        return value


class DeviceRead(ORMModel):
    id: int
    name: str
    address: str
    device_type: str
    vendor: str | None
    model: str | None
    location: str | None
    group_id: int | None
    credential_id: int | None
    enabled: bool
    archived: bool
    monitoring_profile: str
    check_interval: int
    status: str
    last_checked_at: datetime | None
    last_success_at: datetime | None
    is_simulated: bool
    automation_allowed: bool


class CheckRead(ORMModel):
    id: int
    device_id: int
    protocol: str
    success: bool
    latency_ms: float | None
    packet_loss: float | None
    detail: str | None
    is_simulated: bool
    observed_at: datetime


class ConnectionTest(BaseModel):
    protocol: str
    success: bool
    latency_ms: float | None
    packet_loss: float | None
    detail: str


class TargetTest(BaseModel):
    address: str = Field(min_length=1, max_length=253)


class MaintenanceRequest(BaseModel):
    enabled: bool
    note: str | None = Field(default=None, max_length=300)


class MetricRead(ORMModel):
    id: int
    device_id: int
    interface_id: int | None
    name: str
    value: float
    unit: str
    is_simulated: bool
    observed_at: datetime


class DeviceInterfaceRead(ORMModel):
    id: int
    device_id: int
    if_index: int
    name: str
    oper_status: str
    is_uplink: bool
    is_trunk: bool
    remediation_allowed: bool
    updated_at: datetime


class DemoActionRequest(BaseModel):
    action: Literal["enable_interface", "disable_interface", "restart_interface", "reboot_device", "retry_check"]
    interface_id: int | None = None
    confirmed: bool = False


class DemoActionResponse(BaseModel):
    status: Literal["completed"]
    action: str
    detail: str
    is_simulated: bool = True
    device_status: str
    interface: DeviceInterfaceRead | None = None

