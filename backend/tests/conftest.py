import os
from pathlib import Path

os.environ["ISMN_DATABASE_URL"] = "sqlite:///./data/test_ismn.db"
os.environ["ISMN_SECRET_KEY"] = "test-secret-key-with-more-than-thirty-two-characters"
os.environ["ISMN_MONITORING_ENABLED"] = "false"
os.environ["ISMN_ALLOWED_NETWORKS"] = '["127.0.0.0/8","192.168.0.0/16"]'

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import User
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    Path("data/test_ismn.db").unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def clean_database():
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def admin():
    with SessionLocal() as db:
        user = User(username="admin", password_hash=hash_password("StrongPassword123!"), role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture
def admin_headers(client, admin):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "StrongPassword123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

