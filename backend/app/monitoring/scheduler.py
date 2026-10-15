from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select

from app.core.config import get_settings
from app.db.models import Device, MetricSample
from app.db.session import SessionLocal
from app.monitoring.service import check_device


logger = logging.getLogger(__name__)


class MonitoringScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._semaphore = asyncio.Semaphore(get_settings().max_concurrent_checks)

    async def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="ismn-monitoring")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task
            self._task = None

    async def _guarded_check(self, device_id: int) -> None:
        async with self._semaphore:
            try:
                await check_device(device_id)
            except Exception:
                logger.exception("Monitoring check failed for device %s", device_id)

    async def _run(self) -> None:
        tick = get_settings().scheduler_tick_seconds
        while not self._stop.is_set():
            now = datetime.now(timezone.utc)
            with SessionLocal() as db:
                devices = db.scalars(
                    select(Device).where(
                        Device.enabled.is_(True),
                        Device.archived.is_(False),
                        or_(Device.last_checked_at.is_(None), Device.last_checked_at <= now - timedelta(seconds=10)),
                    )
                ).all()
                due = [device.id for device in devices if device.last_checked_at is None or (now - device.last_checked_at.replace(tzinfo=device.last_checked_at.tzinfo or timezone.utc)).total_seconds() >= device.check_interval]
            if due:
                await asyncio.gather(*(self._guarded_check(device_id) for device_id in due))
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=tick)
            except asyncio.TimeoutError:
                pass

    @staticmethod
    def prune_metrics() -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=get_settings().metric_retention_days)
        with SessionLocal() as db:
            result = db.execute(delete(MetricSample).where(MetricSample.observed_at < cutoff))
            db.commit()
            return result.rowcount or 0


monitoring_scheduler = MonitoringScheduler()
