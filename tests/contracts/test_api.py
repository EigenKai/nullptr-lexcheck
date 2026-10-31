import pytest

from contracts.models import CheckResult


def test_fixture_api_matches_schema_without_key(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bundle = client.get("/api/demo").json()
    response = client.post("/api/check", json=bundle["request"])
    assert response.status_code == 200
    result = CheckResult.model_validate(response.json())
    mode = client.get("/health").json()["mode"]
    assert result.mode == mode
    assert result.snapshot.model_dump(mode="json") == bundle["request"]
    if mode == "fixture":
        assert response.json() == bundle["preview"]
    assert client.get("/api/history").status_code == 200


def test_fixture_adapter_does_not_claim_to_check_new_input(client):
    request = client.get("/api/demo").json()["request"]
    request["review_date"] = "2026-10-30"
    response = client.post("/api/check", json=request)
    if client.get("/health").json()["mode"] == "fixture":
        assert response.status_code == 503
        assert response.json()["code"] == "not_ready"
    else:
        assert response.status_code == 200
        assert response.json()["snapshot"]["review_date"] == "2026-10-30"


def test_invalid_input_is_not_echoed(client):
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
def test_pending_operations_return_honest_errors(client, path, body):
    expected = 503 if client.get("/health").json()["mode"] == "fixture" else 404
    assert client.post(path, json=body).status_code == expected


def test_pending_change_does_not_modify_history(client):
    event = client.get("/api/demo").json()["event"]
    if client.get("/health").json()["mode"] == "fixture":
        assert client.post("/api/changes", json=event).status_code == 503
        assert client.get("/api/history").json()["events"] == []
    else:
        response = client.post("/api/changes", json=event)
        assert response.status_code == 200
        assert response.json()["mode"] == "live"


def test_unknown_route_uses_error_contract(client):
    response = client.get("/api/missing")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Resource not found."}
