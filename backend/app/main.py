from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import audit, auth, automations, credentials, devices, incidents, monitoring, reports, topology, users, websocket
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.monitoring.scheduler import monitoring_scheduler


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.monitoring_enabled:
        await monitoring_scheduler.start()
    yield
    if settings.monitoring_enabled:
        await monitoring_scheduler.stop()


app = FastAPI(
    title="ISMN API",
    description="Локальная система авторизованного мониторинга сети. ICMP показывает достижимость, а не полное состояние устройства.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

for router in (auth.router, users.router, credentials.router, devices.router, monitoring.router, incidents.router, automations.router, reports.router, topology.router, audit.router, websocket.router):
    app.include_router(router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception(_: Request, exc: Exception):
    logger.exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


@app.get("/health/live", tags=["Состояние"])
def liveness() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready", tags=["Состояние"])
def readiness() -> dict:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "available", "monitoring": settings.monitoring_enabled}

