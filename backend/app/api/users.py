from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.security import hash_password
from app.db.models import Role, User
from app.db.session import get_db
from app.schemas.auth import UserCreate, UserRead
from app.schemas.common import Page
from app.services.audit import write_audit


router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get("", response_model=Page[UserRead])
def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_roles(Role.admin.value)),
    db: Session = Depends(get_db),
) -> Page[UserRead]:
    total = db.scalar(select(func.count()).select_from(User)) or 0
    items = db.scalars(select(User).order_by(User.username).limit(limit).offset(offset)).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, actor: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="Имя пользователя уже занято")
    user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.flush()
    write_audit(db, "user.create", "user", user.id, actor.id, {"role": user.role})
    db.commit()
    db.refresh(user)
    return user

