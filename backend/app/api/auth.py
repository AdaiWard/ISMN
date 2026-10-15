from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token, new_refresh_token, token_digest, verify_password
from app.db.models import RefreshSession, User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenPair, UserRead
from app.services.audit import write_audit


router = APIRouter(prefix="/auth", tags=["Аутентификация"])
_attempts: defaultdict[str, deque[float]] = defaultdict(deque)


def _rate_limit(key: str) -> None:
    now = time.monotonic()
    attempts = _attempts[key]
    while attempts and attempts[0] < now - 300:
        attempts.popleft()
    if len(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Слишком много попыток. Повторите через несколько минут")
    attempts.append(now)


def _issue_pair(db: Session, user: User) -> TokenPair:
    access, expires = create_access_token(user.id, user.role)
    refresh = new_refresh_token()
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_digest(refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_days),
        )
    )
    return TokenPair(access_token=access, refresh_token=refresh, access_expires_at=expires)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    key = f"{request.client.host if request.client else 'unknown'}:{payload.username.lower()}"
    _rate_limit(key)
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверные учётные данные")
    _attempts.pop(key, None)
    pair = _issue_pair(db, user)
    write_audit(db, "auth.login", "user", user.id, user.id)
    db.commit()
    return pair


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_digest(payload.refresh_token)))
    now = datetime.now(timezone.utc)
    expiry = session.expires_at.replace(tzinfo=session.expires_at.tzinfo or timezone.utc) if session else now
    if not session or session.revoked_at is not None or expiry <= now or not session.user.is_active:
        raise HTTPException(status_code=401, detail="Недействительная refresh-сессия")
    session.revoked_at = now
    pair = _issue_pair(db, session.user)
    write_audit(db, "auth.refresh", "user", session.user_id, session.user_id)
    db.commit()
    return pair


@router.post("/logout", status_code=204, response_class=Response)
def logout(payload: LogoutRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_digest(payload.refresh_token)))
    if session and session.user_id == user.id and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
    write_audit(db, "auth.logout", "user", user.id, user.id)
    db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user

