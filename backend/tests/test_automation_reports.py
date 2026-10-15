from app.automation.engine import validate_interface_action
from app.db.models import AuditLog, AutomationRule, Device, DeviceInterface, MetricSample, MonitoringCheck
from sqlalchemy import select
from app.db.session import SessionLocal


def test_dry_run_and_emergency_pause(client, admin_headers):
    created = client.post(
        "/api/v1/automations/rules",
        headers=admin_headers,
        json={"name": "Notify only", "trigger_key": "reachability_failure", "action_type": "notify", "mode": "dry_run"},
    )
    assert created.status_code == 201
    run = client.post(f"/api/v1/automations/rules/{created.json()['id']}/run", headers=admin_headers)
    assert run.json()["status"] == "simulated"
    assert run.json()["dry_run"] is True
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "automation.run")) is not None
    assert client.put("/api/v1/automations/pause", headers=admin_headers, json={"paused": True}).json()["paused"] is True


def test_manual_approval_lifecycle(client, admin_headers):
    rule = client.post(
        "/api/v1/automations/rules",
        headers=admin_headers,
        json={"name": "Retry with approval", "trigger_key": "reachability_failure", "action_type": "retry_check", "mode": "manual_approval"},
    ).json()
    run = client.post(f"/api/v1/automations/rules/{rule['id']}/run", headers=admin_headers).json()
    assert run["status"] == "pending_approval"
    approved = client.post(f"/api/v1/automations/runs/{run['id']}/approve", headers=admin_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"


def test_forbidden_interface_guards():
    for name, uplink, trunk in (("WAN1", False, False), ("Gi0/1", True, False), ("Gi0/2", False, True)):
        try:
            validate_interface_action(name, uplink, trunk, True)
            assert False, "guard should reject protected interface"
        except ValueError:
            pass
    try:
        validate_interface_action("Gi0/3", False, False, False)
        assert False, "explicit allowlist required"
    except ValueError:
        pass


def test_report_aggregation(client, admin_headers):
    with SessionLocal() as db:
        device = Device(name="report-device", address="127.0.0.1", device_type="server")
        db.add(device)
        db.flush()
        db.add_all([
            MonitoringCheck(device_id=device.id, protocol="icmp", success=True, latency_ms=10, packet_loss=0),
            MonitoringCheck(device_id=device.id, protocol="icmp", success=False, packet_loss=100),
        ])
        db.commit()
    report = client.get("/api/v1/reports/availability?hours=24", headers=admin_headers)
    assert report.status_code == 200
    assert report.json()["items"][0]["observed_availability_percent"] == 50.0
    csv_response = client.get("/api/v1/reports/availability.csv", headers=admin_headers)
    assert csv_response.status_code == 200
    assert "report-device" in csv_response.text


def test_websocket_requires_token(client):
    try:
        with client.websocket_connect("/api/v1/ws/events"):
            assert False, "connection must be rejected"
    except Exception:
        pass


def test_websocket_accepts_access_token(client, admin_headers):
    with client.websocket_connect("/api/v1/ws/events", headers=admin_headers) as socket:
        socket.close()


def test_demo_device_control_is_explicit_and_audited(client, admin_headers):
    created = client.post(
        "/api/v1/devices",
        headers=admin_headers,
        json={
            "name": "Демо-коммутатор",
            "address": "not-a-real-target",
            "device_type": "switch",
            "is_simulated": True,
        },
    )
    assert created.status_code == 201
    device = created.json()
    assert device["is_simulated"] is True
    assert device["automation_allowed"] is True
    assert device["address"].endswith(".simulation.local")

    interfaces = client.get(f"/api/v1/devices/{device['id']}/interfaces", headers=admin_headers).json()
    assert len(interfaces) == 8
    assert interfaces[-1]["is_uplink"] is True
    access_port = interfaces[0]

    missing_confirmation = client.post(
        f"/api/v1/devices/{device['id']}/demo-actions",
        headers=admin_headers,
        json={"action": "disable_interface", "interface_id": access_port["id"]},
    )
    assert missing_confirmation.status_code == 422

    disabled = client.post(
        f"/api/v1/devices/{device['id']}/demo-actions",
        headers=admin_headers,
        json={"action": "disable_interface", "interface_id": access_port["id"], "confirmed": True},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_simulated"] is True
    assert disabled.json()["interface"]["oper_status"] == "down"

    protected = client.post(
        f"/api/v1/devices/{device['id']}/demo-actions",
        headers=admin_headers,
        json={"action": "disable_interface", "interface_id": interfaces[-1]["id"], "confirmed": True},
    )
    assert protected.status_code == 422

    diagnostic = client.post(
        f"/api/v1/devices/{device['id']}/demo-actions",
        headers=admin_headers,
        json={"action": "retry_check", "confirmed": True},
    )
    assert diagnostic.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "demo.control")) is not None
        checks = db.scalars(select(MonitoringCheck).where(MonitoringCheck.device_id == device["id"])).all()
        assert checks and all(check.is_simulated for check in checks)
        metrics = db.scalars(select(MetricSample).where(MetricSample.device_id == device["id"])).all()
        assert metrics and all(metric.is_simulated for metric in metrics)


def test_demo_control_rejects_real_device(client, admin_headers):
    device = client.post(
        "/api/v1/devices",
        headers=admin_headers,
        json={"name": "Real host", "address": "127.0.0.1", "device_type": "server"},
    ).json()
    response = client.post(
        f"/api/v1/devices/{device['id']}/demo-actions",
        headers=admin_headers,
        json={"action": "reboot_device", "confirmed": True},
    )
    assert response.status_code == 409

