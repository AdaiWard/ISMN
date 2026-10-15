import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.security import encrypt_secret
from app.db.models import DeviceCredential, Role, User
from app.db.session import get_db
from app.schemas.credential import CredentialRead, SnmpV3CredentialCreate
from app.services.audit import write_audit


router = APIRouter(prefix="/credentials", tags=["Учётные данные устройств"])


def _read(credential: DeviceCredential) -> dict:
    return {"id": credential.id, "name": credential.name, "protocol": credential.protocol, "created_at": credential.created_at, "has_username": credential.username_encrypted is not None}


@router.get("", response_model=list[CredentialRead])
def list_credentials(_: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)):
    return [_read(item) for item in db.scalars(select(DeviceCredential).order_by(DeviceCredential.name)).all()]


@router.post("/snmpv3", response_model=CredentialRead, status_code=201)
def create_snmp_credential(payload: SnmpV3CredentialCreate, actor: User = Depends(require_roles(Role.admin.value)), db: Session = Depends(get_db)):
    credential = DeviceCredential(
        name=payload.name,
        protocol="snmpv3_authpriv",
        username_encrypted=encrypt_secret(payload.username),
        secret_encrypted=encrypt_secret(json.dumps({"auth_key": payload.auth_key, "priv_key": payload.priv_key})),
        metadata_json={"security_level": "authPriv", "auth_protocol": "SHA", "privacy_protocol": "AES128"},
    )
    db.add(credential)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Профиль с таким именем уже существует") from exc
    write_audit(db, "credential.create", "device_credential", credential.id, actor.id, {"protocol": credential.protocol})
    db.commit()
    db.refresh(credential)
    return _read(credential)

