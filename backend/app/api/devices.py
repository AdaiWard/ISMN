from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.automation.engine import validate_interface_action
from app.core.auth import get_current_user, require_roles
from app.core.config import get_settings
from app.core.network import ensure_target_allowed
from app.db.models import AppSetting, Device, DeviceInterface, DeviceStatus, MetricSample, MonitoringCheck, Role, User
from app.db.session import get_db
from app.monitoring.icmp import ping
from app.monitoring.service import check_device
from app.schemas.common import Page
from app.schemas.device import (
    CheckRead,
    ConnectionTest,
    DemoActionRequest,
    DemoActionResponse,
    DeviceCreate,
    DeviceInterfaceRead,
    DeviceRead,
    DeviceUpdate,
    MaintenanceRequest,
    TargetTest,
)
from app.services.audit import write_audit


router = APIRouter(prefix="/devices", tags=["Устройства"])


def _seed_demo_interfaces(db: Session, device: Device) -> None:
    if device.device_type == "router":
        definitions = [(1, "LAN 1", False), (2, "LAN 2", False), (3, "LAN 3", False), (4, "WAN", True)]
    elif device.device_type in {"pc", "server", "printer"}:
        definitions = [(1, "Ethernet 1", False)]
    else:
        definitions = [(index, f"Port {index}", index == 8) for index in range(1, 9)]
    db.add_all(
        DeviceInterface(
            device_id=device.id,
            if_index=index,
            name=name,
            oper_status="up",
            is_uplink=protected,
            is_trunk=False,
            remediation_allowed=not protected,
        )
        for index, name, protected in definitions
    )


def _get_demo_device(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if not device or device.archived:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    if not device.is_simulated:
        raise HTTPException(status_code=409, detail="Демо-управление доступно только для устройств с меткой ДЕМО / СИМУЛЯЦИЯ")
    return device


@router.get("", response_model=Page[DeviceRead])
def list_devices(
    search: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[DeviceRead]:
    conditions = [Device.archived.is_(False)]
    if search:
        conditions.append(Device.name.ilike(f"%{search}%") | Device.address.ilike(f"%{search}%"))
    if status:
        conditions.append(Device.status == status)
    total = db.scalar(select(func.count()).select_from(Device).where(*conditions)) or 0
    items = db.scalars(select(Device).where(*conditions).order_by(Device.name).limit(limit).offset(offset)).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=DeviceRead, status_code=201)
def create_device(
    payload: DeviceCreate,
    actor: User = Depends(require_roles(Role.admin.value)),
    db: Session = Depends(get_db),
) -> Device:
    if payload.is_simulated:
        address = f"demo-{uuid4().hex[:12]}.simulation.local"
        values = payload.model_dump(exclude={"address"})
        values.update(
            is_simulated=True,
            automation_allowed=True,
            monitoring_profile="test_agent",
            status=DeviceStatus.online.value,
            vendor=payload.vendor or "ISMN Simulator",
            model=payload.model or "Virtual Lab Device",
        )
    else:
        try:
            address = ensure_target_allowed(payload.address)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        values = payload.model_dump(exclude={"address", "is_simulated"})
    device = Device(**values, address=address)
    db.add(device)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Устройство с таким именем или адресом уже существует") from exc
    if device.is_simulated:
        now = datetime.now(timezone.utc)
        _seed_demo_interfaces(db, device)
        db.add_all(
            [
                MonitoringCheck(
                    device_id=device.id,
                    protocol="simulation",
                    success=True,
                    latency_ms=12.0,
                    packet_loss=0.0,
                    detail="ДЕМО / СИМУЛЯЦИЯ: начальное состояние",
                    is_simulated=True,
                    observed_at=now,
                ),
                MetricSample(device_id=device.id, name="ping_latency", value=12.0, unit="ms", is_simulated=True, observed_at=now),
                MetricSample(device_id=device.id, name="cpu_usage", value=24.0, unit="percent", is_simulated=True, observed_at=now),
                MetricSample(device_id=device.id, name="memory_usage", value=38.0, unit="percent", is_simulated=True, observed_at=now),
            ]
        )
        device.last_checked_at = now
        device.last_success_at = now
    write_audit(db, "device.create", "device", device.id, actor.id, {"address": address, "is_simulated": device.is_simulated})
    db.commit()
    db.refresh(device)
    return device


@router.get("/{device_id}/interfaces", response_model=list[DeviceInterfaceRead])
def list_interfaces(device_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DeviceInterface]:
    device = db.get(Device, device_id)
    if not device or device.archived:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return list(db.scalars(select(DeviceInterface).where(DeviceInterface.device_id == device_id).order_by(DeviceInterface.if_index)).all())


@router.post("/{device_id}/demo-actions", response_model=DemoActionResponse)
def run_demo_action(
    device_id: int,
    payload: DemoActionRequest,
    actor: User = Depends(require_roles(Role.admin.value, Role.operator.value)),
    db: Session = Depends(get_db),
) -> dict:
    device = _get_demo_device(db, device_id)
    if not payload.confirmed:
        raise HTTPException(status_code=422, detail="Требуется явное подтверждение демонстрационного действия")
    pause_setting = db.get(AppSetting, "automation_paused")
    if get_settings().automation_paused or bool(pause_setting and pause_setting.value_json.get("paused")):
        raise HTTPException(status_code=409, detail="Автоматизация остановлена аварийной паузой")
    if not device.automation_allowed:
        raise HTTPException(status_code=409, detail="Управление не разрешено для этого устройства")

    interface = None
    interface_actions = {"enable_interface", "disable_interface", "restart_interface"}
    if payload.action in interface_actions:
        if payload.interface_id is None:
            raise HTTPException(status_code=422, detail="Для действия нужно выбрать интерфейс")
        interface = db.get(DeviceInterface, payload.interface_id)
        if not interface or interface.device_id != device.id:
            raise HTTPException(status_code=404, detail="Интерфейс устройства не найден")
        try:
            validate_interface_action(interface.name, interface.is_uplink, interface.is_trunk, interface.remediation_allowed)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    if payload.action == "enable_interface":
        interface.oper_status = "up"
        detail = f"ДЕМО / СИМУЛЯЦИЯ: интерфейс {interface.name} включён"
    elif payload.action == "disable_interface":
        interface.oper_status = "down"
        detail = f"ДЕМО / СИМУЛЯЦИЯ: интерфейс {interface.name} отключён"
    elif payload.action == "restart_interface":
        interface.oper_status = "up"
        detail = f"ДЕМО / СИМУЛЯЦИЯ: интерфейс {interface.name} перезапущен"
    elif payload.action == "reboot_device":
        device.status = DeviceStatus.online.value
        device.last_checked_at = now
        device.last_success_at = now
        detail = "ДЕМО / СИМУЛЯЦИЯ: виртуальное устройство перезагружено"
    else:
        latency = float(8 + (device.id % 7))
        device.status = DeviceStatus.online.value
        device.last_checked_at = now
        device.last_success_at = now
        db.add(MonitoringCheck(device_id=device.id, protocol="simulation", success=True, latency_ms=latency, packet_loss=0.0, detail="ДЕМО / СИМУЛЯЦИЯ: повторная диагностика", is_simulated=True, observed_at=now))
        db.add(MetricSample(device_id=device.id, name="ping_latency", value=latency, unit="ms", is_simulated=True, observed_at=now))
        detail = "ДЕМО / СИМУЛЯЦИЯ: повторная диагностика завершена успешно"

    write_audit(
        db,
        "demo.control",
        "device",
        device.id,
        actor.id,
        {"action": payload.action, "interface_id": payload.interface_id, "is_simulated": True},
    )
    db.commit()
    db.refresh(device)
    if interface is not None:
        db.refresh(interface)
    return {
        "status": "completed",
        "action": payload.action,
        "detail": detail,
        "is_simulated": True,
        "device_status": device.status,
        "interface": interface,
    }


@router.post("/test-target", response_model=ConnectionTest)
async def test_target(payload: TargetTest, _: User = Depends(require_roles(Role.admin.value, Role.operator.value))) -> ConnectionTest:
    try:
        address = ensure_target_allowed(payload.address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = await ping(address)
    return ConnectionTest(protocol="icmp", success=result.success, latency_ms=result.latency_ms, packet_loss=result.packet_loss, detail=result.detail)


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Device:
    device = db.get(Device, device_id)
    if not device or device.archived:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return device


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    actor: User = Depends(require_roles(Role.admin.value)),
    db: Session = Depends(get_db),
) -> Device:
    device = db.get(Device, device_id)
    if not device or device.archived:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    data = payload.model_dump(exclude_unset=True)
    if "address" in data:
        try:
            data["address"] = ensure_target_allowed(data["address"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    for key, value in data.items():
        setattr(device, key, value)
    try:
        write_audit(db, "device.update", "device", device.id, actor.id, {"fields": sorted(data)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Имя или адрес уже используется") from exc
    db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204, response_class=Response)
def archive_device(device_id: int, actor: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)) -> Response:
    device = db.get(Device, device_id)
    if not device or device.archived:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    device.archived = True
    device.enabled = False
    write_audit(db, "device.archive", "device", device.id, actor.id)
    db.commit()
    return Response(status_code=204)


@router.post("/{device_id}/test", response_model=ConnectionTest)
async def test_connection(device_id: int, _: User = Depends(require_roles(Role.admin.value, Role.operator.value)), db: Session = Depends(get_db)) -> ConnectionTest:
    device = db.get(Device, device_id)
    if not device or device.archived:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    result = await ping(device.address)
    return ConnectionTest(protocol="icmp", success=result.success, latency_ms=result.latency_ms, packet_loss=result.packet_loss, detail=result.detail)


@router.post("/{device_id}/check", response_model=CheckRead)
async def run_check(device_id: int, _: User = Depends(require_roles(Role.admin.value, Role.operator.value)), db: Session = Depends(get_db)):
    if not db.get(Device, device_id):
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    check = await check_device(device_id)
    if check is None:
        raise HTTPException(status_code=409, detail="Проверка уже выполняется или мониторинг устройства отключён")
    return check


@router.put("/{device_id}/maintenance", response_model=DeviceRead)
def set_maintenance(
    device_id: int,
    payload: MaintenanceRequest,
    actor: User = Depends(require_roles(Role.admin.value)),
    db: Session = Depends(get_db),
) -> Device:
    device = db.get(Device, device_id)
    if not device or device.archived:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    device.status = DeviceStatus.maintenance.value if payload.enabled else DeviceStatus.unknown.value
    device.consecutive_failures = 0
    device.consecutive_successes = 0
    write_audit(db, "device.maintenance.enable" if payload.enabled else "device.maintenance.disable", "device", device.id, actor.id, {"note": payload.note})
    db.commit()
    db.refresh(device)
    return device

