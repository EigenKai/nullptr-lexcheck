import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    for layer in (1, 2, 3):
        monkeypatch.setenv(f"LEXCHECK_LAYER{layer}_ENABLED", "0")
    with TestClient(create_app()) as session:
        if session.get("/health").json()["mode"] == "live":
            login = session.post("/api/session", json={"user_id": "U-MANAGER"})
            assert login.status_code == 200
            session.headers["Authorization"] = "Bearer " + login.json()["token"]
        yield session
