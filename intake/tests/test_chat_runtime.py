"""Chat uses server runtime policy without changing the checked snapshot."""

import json
from types import SimpleNamespace

import pytest

from contracts.models import CheckResult
from detect.chat import ChatDraft
from detect.client import ModelClient
from detect.validator import WARNING
from intake import auth
from intake.fixtures import load_demo
from intake.tests.test_runtime import login


def prepare_chat(api, monkeypatch):
    monkeypatch.setenv("LEXCHECK_LAYER1_ENABLED", "1")
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "off")
    token = login(api)["token"]
    api.headers["Authorization"] = "Bearer " + token
    request = load_demo().request.model_dump(mode="json")
    request["llm_mode"] = "off"
    targets = []
    for version in tuple(request["versions"]):
        if version["id"] in request["target_version_ids"]:
            changed = {
                **version,
                "id": version["id"] + "-chat",
                "supersedes": version["id"],
                "text": version["text"].replace(WARNING, ""),
            }
            request["versions"].append(changed)
            targets.append(changed["id"])
    request["target_version_ids"] = targets
    response = api.post("/api/check", json=request)
    assert response.status_code == 200
    check = CheckResult.model_validate(response.json())
    assert check.mode == "live" and check.findings
    return check


def stub_model(api, monkeypatch, tmp_path):
    received = []

    def transport(**kwargs):
        payload = json.loads(kwargs["input"])
        received.append(payload)
        return SimpleNamespace(
            status="completed",
            output_parsed=ChatDraft(
                answer="Cần đối chiếu khuyến cáo với điều khoản được trích dẫn.",
                finding_ids=(payload["grounded_findings"][0]["id"],),
            ),
        )

    def client(person, store):
        assert person.group == "manager" and store is api.app.state.store
        return ModelClient(
            model="test-only",
            transport=transport,
            cache_dir=tmp_path / "chat-cache",
            user_id=person.user_id,
            group=person.group,
            acl_hash="test-acl",
        )

    monkeypatch.setattr(auth, "model_client", client)
    return received


@pytest.mark.parametrize("snapshot_mode", ("off", "cache", "live"))
def test_live_chat_uses_server_mode_without_mutating_snapshot(
    api, monkeypatch, tmp_path, snapshot_mode
):
    original = prepare_chat(api, monkeypatch)
    check = original.model_copy(
        update={
            "id": "CHK-chat-" + snapshot_mode,
            "snapshot": original.snapshot.model_copy(update={"llm_mode": snapshot_mode}),
        }
    )
    api.app.state.store.save_check(check)
    received = stub_model(api, monkeypatch, tmp_path)
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    question = "Cần bổ sung khuyến cáo gì?"
    response = api.post("/api/chat", json={"check_id": check.id, "question": question})
    assert response.status_code == 200
    result = response.json()
    assert result["model_status"] == "live" and result["status"] == "answered"
    assert len(received) == 1 and received[0]["question"] == question
    assert result["citations"]
    assert api.app.state.store.checks[check.id] == check
    assert api.get(f"/api/checks/{check.id}").json()["snapshot"]["llm_mode"] == snapshot_mode


@pytest.mark.parametrize("server_mode", (None, "off", "invalid"))
def test_chat_server_mode_fails_closed_even_for_a_live_snapshot(
    api, monkeypatch, tmp_path, server_mode
):
    original = prepare_chat(api, monkeypatch)
    check = original.model_copy(
        update={
            "id": "CHK-chat-live-snapshot",
            "snapshot": original.snapshot.model_copy(update={"llm_mode": "live"}),
        }
    )
    api.app.state.store.save_check(check)
    received = stub_model(api, monkeypatch, tmp_path)
    if server_mode is None:
        monkeypatch.delenv("LEXCHECK_LLM_MODE", raising=False)
    else:
        monkeypatch.setenv("LEXCHECK_LLM_MODE", server_mode)
    result = api.post("/api/chat", json={"check_id": check.id, "question": "Why?"}).json()
    assert result["model_status"] == "off"
    assert not received


def test_cache_only_chat_never_falls_through_to_a_live_call(api, monkeypatch, tmp_path):
    check = prepare_chat(api, monkeypatch)
    received = stub_model(api, monkeypatch, tmp_path)
    question = {"check_id": check.id, "question": "Khuyến cáo nào?"}
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    assert api.post("/api/chat", json=question).json()["model_status"] == "live"
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "cache")
    assert api.post("/api/chat", json=question).json()["model_status"] == "cached"
    question["question"] = "Câu hỏi chưa được lưu?"
    assert api.post("/api/chat", json=question).json()["model_status"] == "unavailable"
    assert len(received) == 1


def run_layer1_chat_smoke(api, monkeypatch, tmp_path):
    check = prepare_chat(api, monkeypatch)
    flags = api.get("/api/features").json()
    assert flags["layer0_ready"] and flags["layer1"]
    real_model_client = auth.model_client
    received = stub_model(api, monkeypatch, tmp_path)
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    question = {"check_id": check.id, "question": "Cần chứng cứ gì?"}

    authorization = api.headers.pop("Authorization")
    assert api.post("/api/chat", json=question).status_code == 401
    assert not received
    api.headers["Authorization"] = authorization

    result = api.post("/api/chat", json=question).json()
    assert result["model_status"] == "live" and result["citations"]
    for citation in result["citations"]:
        clause = next(c for c in check.clause_snapshots if c.id == citation["clause_version_id"])
        assert citation["quote"] in clause.text
    assert len(received) == 1

    # Exercise the real model-client no-credentials branch, without a network call.
    monkeypatch.setattr(auth, "model_client", real_model_client)
    monkeypatch.setenv("LEXCHECK_LAYER1_ENABLED", "1")
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    monkeypatch.setenv("OPENAI_MODEL", "test-only")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LEXCHECK_CACHE_DIR", raising=False)
    result = api.post("/api/chat", json=question).json()
    assert result["model_status"] == "unavailable" and result["citations"]
    assert api.app.state.store.checks[check.id] == check

    monkeypatch.setenv("LEXCHECK_LAYER1_ENABLED", "0")
    assert api.post("/api/chat", json=question).status_code == 404
