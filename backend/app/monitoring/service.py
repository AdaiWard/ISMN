from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation.engine import run_matching_rules
from app.core.config import get_settings
from app.core.network import ensure_target_allowed
from app.core.security import decrypt_secret
from app.db.models import Device, DeviceStatus, Incident, IncidentEvent, IncidentStatus, MetricSample, MonitoringCheck
from app.db.session import SessionLocal
from app.monitoring.icmp import PingResult, ping
from app.monitoring.baseline import evaluate_moving_baseline
from app.monitoring.snmp import collect_snmp_v3
from app.services.events import event_hub


_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def _active_reachability_incident(db: Session, device_id: int) -> Incident | None:
    return db.scalar(
        select(Incident).where(
            Incident.device_id == device_id,
            Incident.rule_key == "reachability_failure",
            Incident.status.in_([IncidentStatus.open.value, IncidentStatus.acknowledged.value]),
        )
    )


def _active_incident(db: Session, device_id: int, rule_key: str) -> Incident | None:
    return db.scalar(
        select(Incident).where(
            Incident.device_id == device_id,
            Incident.rule_key == rule_key,
            Incident.status.in_([IncidentStatus.open.value, IncidentStatus.acknowledged.value]),
        )
    )


def apply_ping_result(db: Session, device: Device, result: PingResult) -> tuple[MonitoringCheck, Incident | None, str | None]:
    now = datetime.now(timezone.utc)
    check = MonitoringCheck(
        device_id=device.id,
        protocol="icmp",
        success=result.success,
        latency_ms=result.latency_ms,
        packet_loss=result.packet_loss,
        detail=result.detail,
        is_simulated=False,
        observed_at=now,
    )
    db.add(check)
    if result.latency_ms is not None:
        db.add(MetricSample(device_id=device.id, name="ping_latency", value=result.latency_ms, unit="ms", observed_at=now))
    db.add(MetricSample(device_id=device.id, name="packet_loss", value=result.packet_loss, unit="percent", observed_at=now))
    device.last_checked_at = now
    event_type = None
    incident = _active_reachability_incident(db, device.id)
    if result.success:
        device.consecutive_successes += 1
        device.consecutive_failures = 0
        device.last_success_at = now
        if device.status != DeviceStatus.online.value and device.consecutive_successes >= 2:
            device.status = DeviceStatus.online.value
            event_type = "device.recovered"
            if incident:
                incident.status = IncidentStatus.resolved.value
                incident.resolved_at = now
                db.add(IncidentEvent(incident_id=incident.id, event_type="recovered", message="Восстановление подтверждено двумя успешными ICMP-проверками"))
        if result.latency_ms is not None:
            recent_checks = db.scalars(
                select(MonitoringCheck)
                .where(MonitoringCheck.device_id == device.id, MonitoringCheck.success.is_(True), MonitoringCheck.latency_ms.is_not(None))
                .order_by(MonitoringCheck.observed_at.desc())
                .limit(3)
            ).all()
            high_latency = _active_incident(db, device.id, "high_latency")
            if len(recent_checks) >= 3 and all((item.latency_ms or 0) > 200 for item in recent_checks) and high_latency is None:
                historical = list(db.scalars(select(MetricSample.value).where(MetricSample.device_id == device.id, MetricSample.name == "ping_latency").order_by(MetricSample.observed_at.desc()).limit(50)).all())
                baseline = evaluate_moving_baseline(list(reversed(historical)), result.latency_ms)
                high_latency = Incident(
                    device_id=device.id,
                    rule_key="high_latency",
                    severity="warning",
                    title=f"Устойчивая задержка на {device.name}",
                    explanation=f"Правило builtin.high_latency: 3 наблюдения подряд выше 200 мс; текущее {result.latency_ms:.1f} мс. Базовая линия: {baseline.explanation}",
                    opened_at=now,
                )
                db.add(high_latency)
                db.flush()
                db.add(IncidentEvent(incident_id=high_latency.id, event_type="opened", message=high_latency.explanation))
                run_matching_rules(db, high_latency)
                device.status = DeviceStatus.degraded.value
                incident = high_latency
                event_type = "incident.opened"
            elif high_latency is not None and result.latency_ms < 160:
                high_latency.status = IncidentStatus.resolved.value
                high_latency.resolved_at = now
                db.add(IncidentEvent(incident_id=high_latency.id, event_type="recovered", message="Задержка опустилась ниже порога восстановления 160 мс"))
                event_type = "incident.resolved"
            elif high_latency is not None:
                device.status = DeviceStatus.degraded.value
    else:
        device.consecutive_failures += 1
        device.consecutive_successes = 0
        if device.status == DeviceStatus.online.value:
            device.status = DeviceStatus.degraded.value
        if device.consecutive_failures >= 3 and device.status != DeviceStatus.maintenance.value:
            device.status = DeviceStatus.offline.value
            if incident is None:
                incident = Incident(
                    device_id=device.id,
                    rule_key="reachability_failure",
                    severity="critical",
                    title=f"Устройство {device.name} не отвечает",
                    explanation=f"Три последовательные ICMP-проверки завершились без ответа. Это не доказывает отказ питания или кабеля: ICMP может быть заблокирован. Последнее наблюдение: {result.detail}",
                    opened_at=now,
                )
                db.add(incident)
                db.flush()
                db.add(IncidentEvent(incident_id=incident.id, event_type="opened", message=incident.explanation))
                run_matching_rules(db, incident)
                event_type = "incident.opened"
    db.flush()
    return check, incident, event_type


async def check_device(device_id: int) -> MonitoringCheck | None:
    lock = _locks[device_id]
    if lock.locked():
        return None
    async with lock:
        with SessionLocal() as db:
            device = db.get(Device, device_id)
            if not device or not device.enabled or device.archived or device.status == DeviceStatus.maintenance.value:
                return None
            if device.is_simulated:
                now = datetime.now(timezone.utc)
                latency = float(8 + (device.id % 7))
                check = MonitoringCheck(
                    device_id=device.id,
                    protocol="simulation",
                    success=True,
                    latency_ms=latency,
                    packet_loss=0.0,
                    detail="ДЕМО / СИМУЛЯЦИЯ: виртуальная проверка выполнена",
                    is_simulated=True,
                    observed_at=now,
                )
                db.add(check)
                db.add(MetricSample(device_id=device.id, name="ping_latency", value=latency, unit="ms", is_simulated=True, observed_at=now))
                db.add(MetricSample(device_id=device.id, name="cpu_usage", value=float(20 + (device.id % 15)), unit="percent", is_simulated=True, observed_at=now))
                device.status = DeviceStatus.online.value
                device.last_checked_at = now
                device.last_success_at = now
                device.consecutive_successes += 1
                device.consecutive_failures = 0
                db.commit()
                db.refresh(check)
                return check
            try:
                target = ensure_target_allowed(device.address)
                result = await ping(target, get_settings().ping_timeout_seconds)
            except ValueError as exc:
                result = PingResult(False, None, 100.0, f"Адрес больше не проходит allowlist: {exc}")
            check, incident, event_type = apply_ping_result(db, device, result)
            if result.success and device.monitoring_profile == "icmp_snmp":
                if device.credential and device.credential.protocol == "snmpv3_authpriv":
                    secrets = json.loads(decrypt_secret(device.credential.secret_encrypted))
                    snmp = await collect_snmp_v3(
                        target=device.address,
                        username=decrypt_secret(device.credential.username_encrypted or ""),
                        auth_key=secrets["auth_key"],
                        priv_key=secrets["priv_key"],
                    )
                    db.add(MonitoringCheck(device_id=device.id, protocol="snmpv3", success=snmp.success, detail=snmp.detail))
                    if snmp.success and "uptime_ticks" in snmp.values:
                        db.add(MetricSample(device_id=device.id, name="uptime", value=float(snmp.values["uptime_ticks"]) / 100, unit="seconds"))
                    elif device.status == DeviceStatus.online.value:
                        device.status = DeviceStatus.degraded.value
                else:
                    db.add(MonitoringCheck(device_id=device.id, protocol="snmpv3", success=False, detail="SNMPv3 профиль не назначен; метрики не выдумываются"))
            db.commit()
            db.refresh(check)
            if event_type:
                await event_hub.publish(
                    {"type": event_type, "device_id": device.id, "incident_id": incident.id if incident else None, "timestamp": datetime.now(timezone.utc).isoformat()}
                )
            return check

