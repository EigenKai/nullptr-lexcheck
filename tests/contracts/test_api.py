import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fixture_api_matches_schema_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bundle = client.get("/api/demo").json()
    response = client.post("/api/check", json=bundle["request"])
    assert response.status_code == 200
    assert response.json() == bundle["preview"]
    assert client.get("/health").json() == {"status": "ok", "mode": "fixture"}
    assert client.get("/api/history").json()["mode"] == "fixture"


def test_fixture_adapter_does_not_claim_to_check_new_input():
    request = client.get("/api/demo").json()["request"]
    request["review_date"] = "2026-10-30"
    response = client.post("/api/check", json=request)
    assert response.status_code == 503
    assert response.json()["code"] == "not_ready"


def test_invalid_input_is_not_echoed():
    response = client.post("/api/check", json={"secret": "do-not-echo-this"})
    assert response.status_code == 422
    assert "do-not-echo-this" not in response.text


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/rechecks", {"item_id": "RQ-01"}),
        (
            "/api/decisions",
            {
                "check_id": "CHK-01",
                "finding_id": "F-01",
                "action": "confirm",
                "actor": "reviewer",
                "note": "Synthetic review",
            },
        ),
    ],
)
def test_pending_operations_return_honest_errors(path, body):
    assert client.post(path, json=body).status_code == 503


def test_pending_change_does_not_modify_history():
    event = client.get("/api/demo").json()["event"]
    assert client.post("/api/changes", json=event).status_code == 503
    assert client.get("/api/history").json()["events"] == []


def test_unknown_route_uses_error_contract():
    response = client.get("/api/missing")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Resource not found."}
