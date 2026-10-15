from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.automation.engine import create_run
from app.core.auth import get_current_user, require_roles
from app.db.models import AppSetting, AutomationRule, AutomationRun, Role, User
from app.db.session import get_db
from app.schemas.automation import AutomationRuleCreate, AutomationRuleRead, AutomationRunRead, PauseRequest
from app.schemas.common import Page
from app.services.audit import write_audit


router = APIRouter(prefix="/automations", tags=["Автоматизация"])


@router.get("/status")
def automation_status(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    setting = db.get(AppSetting, "automation_paused")
    return {"paused": bool(setting and setting.value_json.get("paused")), "default_mode": "dry_run"}


@router.put("/pause")
def set_pause(payload: PauseRequest, actor: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)) -> dict:
    setting = db.get(AppSetting, "automation_paused") or AppSetting(key="automation_paused")
    setting.value_json = {"paused": payload.paused}
    db.add(setting)
    write_audit(db, "automation.pause" if payload.paused else "automation.resume", "app_setting", setting.key, actor.id)
    db.commit()
    return {"paused": payload.paused}


@router.get("/rules", response_model=list[AutomationRuleRead])
def list_rules(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(AutomationRule).order_by(AutomationRule.name)).all()


@router.post("/rules", response_model=AutomationRuleRead, status_code=201)
def create_rule(payload: AutomationRuleCreate, actor: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)):
    if payload.action_type == "reenable_interface" and payload.mode == "active":
        raise HTTPException(status_code=422, detail="Сетевое SSH-действие доступно только с ручным одобрением")
    rule = AutomationRule(**payload.model_dump(), created_by=actor.id)
    db.add(rule)
    db.flush()
    write_audit(db, "automation_rule.create", "automation_rule", rule.id, actor.id, {"mode": rule.mode, "action": rule.action_type})
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/rules/{rule_id}/run", response_model=AutomationRunRead)
def run_rule(rule_id: int, actor: User = Depends(require_roles(Role.admin.value, Role.operator.value)), db: Session = Depends(get_db)):
    rule = db.get(AutomationRule, rule_id)
    if not rule or not rule.enabled:
        raise HTTPException(status_code=404, detail="Активное правило не найдено")
    run = create_run(db, rule, None, actor.id)
    db.commit()
    db.refresh(run)
    return run


@router.get("/runs", response_model=Page[AutomationRunRead])
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(AutomationRun)) or 0
    items = db.scalars(select(AutomationRun).order_by(AutomationRun.started_at.desc()).limit(limit).offset(offset)).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.post("/runs/{run_id}/approve", response_model=AutomationRunRead)
def approve_run(run_id: int, actor: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)):
    run = db.get(AutomationRun, run_id)
    if not run or run.status != "pending_approval":
        raise HTTPException(status_code=409, detail="Запуск не ожидает одобрения")
    rule = db.get(AutomationRule, run.rule_id)
    if rule.action_type == "reenable_interface":
        run.status = "blocked"
        run.detail = "SSH-драйвер оборудования не настроен; команда не выполнялась"
    else:
        run.status = "completed"
        run.detail = f"Безопасное действие {rule.action_type} одобрено и выполнено"
    run.approved_by = actor.id
    run.finished_at = datetime.now(timezone.utc)
    write_audit(db, "automation.approve", "automation_run", run.id, actor.id, {"status": run.status})
    db.commit()
    db.refresh(run)
    return run

