from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import Device, Incident, IncidentEvent, MetricSample
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        device = db.scalar(select(Device).where(Device.name == "ДЕМО — маршрутизатор"))
        if not device:
            device = Device(
                name="ДЕМО — маршрутизатор",
                address="127.0.0.1",
                device_type="router",
                monitoring_profile="icmp",
                status="degraded",
                enabled=False,
                is_simulated=True,
            )
            db.add(device)
            db.flush()
        db.query(MetricSample).filter(MetricSample.device_id == device.id, MetricSample.is_simulated.is_(True)).delete()
        start = datetime.now(timezone.utc) - timedelta(minutes=20)
        scripted = [18, 19, 21, 24, 40, 85, 160, 240, 180, 90, 35, 22]
        for index, value in enumerate(scripted):
            db.add(MetricSample(device_id=device.id, name="ping_latency", value=value, unit="ms", is_simulated=True, observed_at=start + timedelta(minutes=index)))
        if not db.scalar(select(Incident).where(Incident.device_id == device.id, Incident.rule_key == "demo_script")):
            incident = Incident(device_id=device.id, rule_key="demo_script", severity="warning", title="ДЕМО / СИМУЛЯЦИЯ: рост задержки", explanation="Сценарий seed_demo: синтетическая задержка превысила 150 мс. Эти данные не получены с физического оборудования.")
            db.add(incident)
            db.flush()
            db.add(IncidentEvent(incident_id=incident.id, event_type="simulated", message="ДЕМО / СИМУЛЯЦИЯ: воспроизводимый сценарий"))
        db.commit()
        print("Seeded deterministic DEMO / SIMULATION data. It is segregated with is_simulated=true.")


if __name__ == "__main__":
    main()

