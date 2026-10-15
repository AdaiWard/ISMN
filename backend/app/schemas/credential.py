from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class SnmpV3CredentialCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    username: str = Field(min_length=1, max_length=64)
    auth_key: str = Field(min_length=8, max_length=256)
    priv_key: str = Field(min_length=8, max_length=256)


class CredentialRead(ORMModel):
    id: int
    name: str
    protocol: str
    created_at: datetime
    has_username: bool = True

