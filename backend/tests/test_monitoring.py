import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import select

from app.db.models import Device, Incident, MetricSample, MonitoringCheck
from app.db.session import SessionLocal
from app.monitoring.icmp import PingResult, build_ping_command, parse_ping_output, ping
from app.monitoring.snmp import collect_snmp_v3, counter_rate
from app.monitoring.service import apply_ping_result, check_device


def test_ping_command_is_fixed_argument_list():
    command = build_ping_command("127.0.0.1", 2, 2)
    assert isinstance(command, list)
    assert command[-1] == "127.0.0.1"
    assert ";" not in " ".join(command)


def test_ping_parser_success_and_failure():
    success = parse_ping_output(0, "Reply from 127.0.0.1: time<1ms TTL=128\nReply: time=2ms", 2)
    assert success.success and success.packet_loss == 0
    failure = parse_ping_output(1, "Request timed out.", 2)
    assert not failure.success and failure.packet_loss == 100
    localized = parse_ping_output(0, "Ответ от 127.0.0.1: время<1мс TTL=128\nОтвет: время=2мс", 2)
    assert localized.latency_ms == 1.5


@pytest.mark.asyncio
async def test_ping_timeout_is_reported():
    process = AsyncMock()
    process.kill = Mock()
    process.communicate.side_effect = TimeoutError
    process.wait.return_value = 0
    with patch("asyncio.create_subprocess_exec", return_value=process):
        result = await ping("127.0.0.1", timeout_seconds=0.01, count=1)
    assert not result.success
    assert "Тайм-аут" in result.detail


def test_hysteresis_incident_recovery_and_durable_metrics():
    with SessionLocal() as db:
        device = Device(name="router", address="127.0.0.1", device_type="router")
        db.add(device)
        db.commit()
        for _ in range(3):
            apply_ping_result(db, device, PingResult(False, None, 100, "no answer"))
            db.commit()
        assert device.status == "offline"
        assert db.scalar(select(Incident).where(Incident.device_id == device.id)).status == "open"
        for _ in range(2):
            apply_ping_result(db, device, PingResult(True, 4.0, 0, "ok"))
            db.commit()
        assert device.status == "online"
        assert db.scalar(select(Incident).where(Incident.device_id == device.id)).status == "resolved"
        assert len(db.scalars(select(MonitoringCheck)).all()) == 5
        assert len(db.scalars(select(MetricSample)).all()) >= 5


def test_only_one_open_incident_during_repeated_failures():
    with SessionLocal() as db:
        device = Device(name="switch", address="127.0.0.2", device_type="switch")
        db.add(device)
        db.commit()
        for _ in range(8):
            apply_ping_result(db, device, PingResult(False, None, 100, "no answer"))
            db.commit()
        assert len(db.scalars(select(Incident)).all()) == 1


def test_snmp_counter_rate_wrap_and_restart_guard():
    assert counter_rate(100, 300, 10) == 20
    assert counter_rate(2**32 - 20, 20, 2, bits=32) == 20
    assert counter_rate(2**63, 10, 1, bits=64) is None


def test_sustained_latency_opens_one_explained_incident():
    with SessionLocal() as db:
        device = Device(name="slow-router", address="127.0.0.3", device_type="router")
        db.add(device)
        db.commit()
        for value in (210.0, 240.0, 260.0, 280.0):
            apply_ping_result(db, device, PingResult(True, value, 0, "ok"))
            db.commit()
        incidents = db.scalars(select(Incident).where(Incident.rule_key == "high_latency")).all()
        assert len(incidents) == 1
        assert "3 наблюдения" in incidents[0].explanation
        assert "200 мс" in incidents[0].explanation


@pytest.mark.asyncio
async def test_snmp_timeout_is_explained():
    result = await collect_snmp_v3(target="127.0.0.1", username="nobody", auth_key="auth-pass", priv_key="priv-pass", timeout=0.01)
    assert result.success is False
    assert "SNMP" in result.detail


@pytest.mark.asyncio
async def test_concurrent_check_is_prevented():
    with SessionLocal() as db:
        device = Device(name="locked-device", address="127.0.0.5", device_type="server")
        db.add(device)
        db.commit()
        device_id = device.id
    started = asyncio.Event()
    release = asyncio.Event()

    async def delayed_ping(*_args, **_kwargs):
        started.set()
        await release.wait()
        return PingResult(True, 1, 0, "ok")

    with patch("app.monitoring.service.ping", side_effect=delayed_ping):
        first = asyncio.create_task(check_device(device_id))
        await started.wait()
        assert await check_device(device_id) is None
        release.set()
        assert await first is not None

