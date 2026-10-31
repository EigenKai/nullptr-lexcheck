"""Route-policy unit tests: open the feature gate only, never replace the legal engine.

These tests exercise authorization/validation/error handling, not a live layer smoke.
"""

import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from contracts.models import ChatCitation, ChatResponse, LegalChangeEvent
from intake import auth, layer_routes
from intake.fixtures import load_demo
from intake.tests.test_runtime import login


@pytest.fixture
def authorized(api, monkeypatch):
    token = login(api)["token"]
    api.headers["Authorization"] = "Bearer " + token
    monkeypatch.setattr(layer_routes, "gate", lambda _layer: None)
    return api


def event():
    return json.loads(Path("data/fixtures/layers.json").read_text(encoding="utf-8"))[
        "LegalChangeEvent"
    ]


def test_pending_update_does_not_replace_active_rules(authorized):
    before = Path("rules/catalog.json").read_bytes()
    data = event()
    response = authorized.post("/api/legal-changes", json=data)
    assert response.status_code == 200
    assert response.json()["state"]["status"] == "pending"
    assert authorized.post("/api/legal-changes", json=data).json() == response.json()
    assert Path("rules/catalog.json").read_bytes() == before
    assert (
        authorized.post(
            f"/api/legal-changes/{data['id']}/activate", json={"review_date": "2026-10-31"}
        ).status_code
        == 409
    )


def test_unverified_interpretation_cannot_be_accepted(authorized):
    data = event()
    authorized.post("/api/legal-changes", json=data)
    response = authorized.post(
        f"/api/legal-changes/{data['id']}/review", json={"action": "accept", "note": "Synthetic"}
    )
    assert response.status_code == 409
    assert authorized.app.state.store.legal_changes[data["id"]].status == "pending"


def test_rejected_interpretation_keeps_audit_and_old_check(authorized):
    data = event()
    old = load_demo().preview
    authorized.app.state.store.save_check(old)
    authorized.post("/api/legal-changes", json=data)
    response = authorized.post(
        f"/api/legal-changes/{data['id']}/review",
        json={"action": "reject", "note": "Need a verified source."},
    )
    assert response.status_code == 200
    assert authorized.app.state.store.checks[old.id] == old
    assert authorized.app.state.store.data.audit[-1].note == "Need a verified source."


def test_chat_without_owner_module_reports_unavailable(authorized):
    old = load_demo().preview
    authorized.app.state.store.save_check(old)
    response = authorized.post(
        "/api/chat", json={"check_id": old.id, "question": "What evidence is missing?"}
    )
    assert response.status_code == 200
    assert response.json()["model_status"] == "unavailable"
    assert response.json()["citations"] == []


def test_chat_authorizes_before_reading_owner_context(authorized, monkeypatch):
    old = load_demo().preview
    authorized.app.state.store.save_check(old)
    authorized.app.state.sessions["ops-unit-token"] = auth.Principal(
        "U-OPS", "operations", auth.now() + timedelta(hours=1)
    )
    authorized.headers["Authorization"] = "Bearer ops-unit-token"

    def forbidden(_name):
        raise AssertionError("Private snapshot reached the chat module")

    monkeypatch.setattr(layer_routes.service, "owner_module", forbidden)
    assert (
        authorized.post(
            "/api/chat", json={"check_id": old.id, "question": "Private data?"}
        ).status_code
        == 404
    )


def test_chat_rejects_a_fabricated_clause(authorized, monkeypatch):
    old = load_demo().preview
    authorized.app.state.store.save_check(old)
    answer = ChatResponse(
        status="answered",
        answer="Synthetic unsupported output",
        citations=(ChatCitation(clause_version_id="CV-FABRICATED", quote="No such citation"),),
        model_status="cached",
    )
    monkeypatch.setattr(
        layer_routes.service,
        "owner_module",
        lambda _name: SimpleNamespace(answer=lambda *_args: answer),
    )
    response = authorized.post("/api/chat", json={"check_id": old.id, "question": "Why?"})
    assert response.json()["status"] == "needs_evidence"
    assert response.json()["citations"] == []


def test_legal_activation_rejects_future_dates():
    from datetime import date

    from contracts.models import LegalChangeState
    from intake import service

    state = LegalChangeState(event=LegalChangeEvent.model_validate(event()))
    with pytest.raises(HTTPException) as exc:
        service.can_activate(state, date(2026, 1, 1))
    assert exc.value.status_code == 409


def test_evaluation_has_no_invented_score(authorized):
    response = authorized.get("/api/evaluation")
    assert response.status_code == 200
    data = response.json()
    if not Path("eval/results/latest.json").exists():
        assert data["n"] == 0 and data["systems"] == []
