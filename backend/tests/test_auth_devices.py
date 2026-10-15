import sys

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.db.session import SessionLocal
from scripts.create_admin import main as create_admin


def test_admin_cli_initialization(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["create_admin", "--username", "cliadmin", "--password", "StrongCliPassword123!"])
    create_admin()
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "cliadmin").one()
        assert user.role == "admin"
        assert verify_password("StrongCliPassword123!", user.password_hash)


def test_login_refresh_logout(client, admin):
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "StrongPassword123!"})
    assert login.status_code == 200
    tokens = login.json()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.json()["role"] == "admin"
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert logout.status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refreshed.json()["refresh_token"]}).status_code == 401


def test_device_crud_duplicate_and_allowlist(client, admin_headers):
    payload = {"name": "Локальный сервер", "address": "127.0.0.1", "device_type": "server", "monitoring_profile": "icmp", "check_interval": 30}
    created = client.post("/api/v1/devices", headers=admin_headers, json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "unknown"
    assert client.post("/api/v1/devices", headers=admin_headers, json={**payload, "name": "Другой"}).status_code == 409
    assert client.post("/api/v1/devices", headers=admin_headers, json={**payload, "name": "Internet", "address": "8.8.8.8"}).status_code == 422
    device_id = created.json()["id"]
    updated = client.patch(f"/api/v1/devices/{device_id}", headers=admin_headers, json={"location": "Лаборатория"})
    assert updated.json()["location"] == "Лаборатория"
    assert client.delete(f"/api/v1/devices/{device_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/v1/devices/{device_id}", headers=admin_headers).status_code == 404


def test_rbac_viewer_cannot_create_device(client):
    with SessionLocal() as db:
        db.add(User(username="viewer", password_hash=hash_password("ViewerPassword123!"), role="viewer"))
        db.commit()
    token = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "ViewerPassword123!"}).json()["access_token"]
    response = client.post(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Denied", "address": "127.0.0.1", "device_type": "server"},
    )
    assert response.status_code == 403

