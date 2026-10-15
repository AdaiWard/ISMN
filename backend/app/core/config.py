from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="ISMN_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ISMN"
    environment: str = "development"
    database_url: str = "sqlite:///./data/ismn.db"
    secret_key: str
    credential_master_key: str | None = None
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    allowed_networks: list[str] = Field(
        default_factory=lambda: ["127.0.0.0/8", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])
    monitoring_enabled: bool = True
    automation_paused: bool = False
    metric_retention_days: int = 30
    log_level: str = "INFO"
    ping_timeout_seconds: float = 2.0
    scheduler_tick_seconds: int = 5
    max_concurrent_checks: int = 20

    @field_validator("secret_key")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("ISMN_SECRET_KEY must contain at least 32 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

