import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LEXCHECK_STATE_FILE", str(tmp_path / "state.json"))
    for layer in (1, 2, 3):
        monkeypatch.setenv(f"LEXCHECK_LAYER{layer}_ENABLED", "0")
    with TestClient(create_app()) as client:
        yield client
