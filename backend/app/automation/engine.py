from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AppSetting, AutomationRule, AutomationRun, Device, Incident
from app.services.audit import write_audit


SAFE_ACTIONS = {"notify", "retry_check"}
FORBIDDEN_INTERFACE_MARKERS = {"uplink", "trunk", "management", "mgmt", "wan"}


def validate_interface_action(interface_name: str, is_uplink: bool, is_trunk: bool, explicitly_allowed: bool) -> None:
    lowered = interface_name.lower()
    if is_uplink or is_trunk or any(marker in lowered for marker in FORBIDDEN_INTERFACE_MARKERS):
        raise ValueError("Защищённый uplink/trunk/management-интерфейс изменять запрещено")
    if not explicitly_allowed:
        raise ValueError("Интерфейс не включён в явный allowlist")


def create_run(db: Session, rule: AutomationRule, incident: Incident | None, actor_id: int | None = None) -> AutomationRun:
    settings = get_settings()
    device = db.get(Device, rule.device_id) if rule.device_id else None
    dry_run = rule.mode == "dry_run"
    requires_approval = rule.mode == "manual_approval"

    pause_setting = db.get(AppSetting, "automation_paused")
    paused = settings.automation_paused or bool(pause_setting and pause_setting.value_json.get("paused"))
    if paused:
        status, detail = "blocked", "Глобальная автоматизация приостановлена"
    elif rule.action_type not in SAFE_ACTIONS:
        status, detail = "pending_approval", "Активное сетевое действие требует отдельного проверенного драйвера и одобрения"
        requires_approval = True
    elif rule.mode == "active" and device and not device.automation_allowed:
        status, detail = "blocked", "Автоматизация не разрешена для устройства"
    elif dry_run:
        status, detail = "simulated", f"DRY-RUN: действие {rule.action_type} не выполнялось"
    elif requires_approval:
        status, detail = "pending_approval", "Ожидается одобрение администратора"
    else:
        status, detail = "completed", f"Безопасное действие {rule.action_type} выполнено"

    run = AutomationRun(
        rule_id=rule.id,
        incident_id=incident.id if incident else None,
        status=status,
        dry_run=dry_run,
        requires_approval=requires_approval,
        detail=detail,
        finished_at=datetime.now(timezone.utc) if status in {"blocked", "simulated", "completed"} else None,
    )
    db.add(run)
    db.flush()
    write_audit(db, "automation.run", "automation_run", run.id, actor_id, {"status": status, "rule_id": rule.id})
    return run


def run_matching_rules(db: Session, incident: Incident) -> list[AutomationRun]:
    rules = db.scalars(
        select(AutomationRule).where(
            AutomationRule.enabled.is_(True),
            AutomationRule.trigger_key == incident.rule_key,
            (AutomationRule.device_id.is_(None) | (AutomationRule.device_id == incident.device_id)),
        )
    ).all()
    return [create_run(db, rule, incident) for rule in rules]

