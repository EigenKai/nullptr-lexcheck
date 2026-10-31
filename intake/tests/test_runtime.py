from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from intake.fixtures import load_demo


def login(client, user="U-MANAGER"):
    response = client.post("/api/session", json={"user_id": user})
    assert response.status_code == 200
    return response.json()


def test_session_is_server_issued_and_not_persisted(api, tmp_path):
    session = login(api)
    assert len(session["token"]) >= 32
    assert session["group"] == "manager"
    assert session["token"] != login(api)["token"]
    path = tmp_path / "state.json"
    assert not path.exists() or session["token"] not in path.read_text(encoding="utf-8")


def test_operations_session_is_unavailable_before_layer3(api):
    assert api.post("/api/session", json={"user_id": "U-OPS"}).status_code == 404


def test_expired_session_cannot_decide(api):
    from intake.auth import Principal

    session = login(api)
    api.app.state.sessions[session["token"]] = Principal(
        "U-MANAGER", "manager", datetime.now(UTC) - timedelta(seconds=1)
    )
    api.headers["Authorization"] = "Bearer " + session["token"]
    response = api.post(
        "/api/decisions",
        json={
            "check_id": "CHK-unknown",
            "finding_id": "F-unknown",
            "action": "confirm",
            "actor": "reviewer",
            "note": "Synthetic review",
        },
    )
    assert response.status_code == 401


def test_create_app_store_is_isolated(api, monkeypatch, tmp_path):
    session = login(api)
    monkeypatch.setenv("LEXCHECK_STATE_FILE", str(tmp_path / "other.json"))
    with TestClient(create_app()) as other:
        assert other.app.state.store is not api.app.state.store
        assert session["token"] not in other.app.state.sessions


def test_bootstrap_does_not_claim_a_live_pipeline(api):
    assert api.get("/health").json()["mode"] == "fixture"
    assert api.get("/api/features").json()["layer0_ready"] is False
    changed = load_demo().request.model_dump(mode="json")
    changed["review_date"] = "2026-10-30"
    assert api.post("/api/check", json=changed).status_code == 503


def test_claimed_use_must_exist_in_original_text(api):
    changed = load_demo().request.model_dump(mode="json")
    changed["versions"][0]["uses"] = ["Synthetic absent use"]
    response = api.post("/api/check", json=changed)
    assert response.status_code == 422
    assert "Synthetic absent use" not in response.text


def test_http_feature_flags_fail_closed_when_engine_is_not_ready(api, monkeypatch):
    monkeypatch.setenv("LEXCHECK_LAYER1_ENABLED", "1")
    assert api.get("/api/features").json()["layer1"] is False
    response = api.post("/api/chat", json={"check_id": "CHK-01", "question": "Why?"})
    assert response.status_code == 404


def test_store_keeps_versions_immutable_and_reloads(api, tmp_path):
    from intake.store import Store

    store = api.app.state.store
    preview = load_demo().preview
    store.save_check(preview)
    assert Store(tmp_path / "state.json").checks[preview.id] == preview
    changed = preview.model_copy(update={"summary": "Different payload"})
    with pytest.raises(Exception) as error:
        store.save_check(changed)
    assert getattr(error.value, "status_code", None) == 409
    assert store.checks[preview.id] == preview


def test_atomic_write_failure_keeps_previous_state(api, monkeypatch):
    from intake import store as module

    store = api.app.state.store

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(module.os, "replace", fail)
    with pytest.raises(OSError):
        store.save_check(load_demo().preview)
    assert store.checks == {}
