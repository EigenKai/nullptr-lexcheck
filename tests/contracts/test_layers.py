import pytest
from pydantic import ValidationError

from contracts.models import ChatResponse, FeatureFlags, LegalChangeEvent


def test_later_layer_requires_all_previous_layers():
    with pytest.raises(ValidationError):
        FeatureFlags(layer0_ready=True, layer2=True)


def test_answered_chat_requires_citations():
    with pytest.raises(ValidationError):
        ChatResponse(status="answered", answer="A claim without sources.", citations=())


def test_legal_event_cannot_activate_a_different_effective_date():
    from intake.fixtures import load_demo

    clause = load_demo().clauses[0].model_dump(mode="json")
    with pytest.raises(ValidationError):
        LegalChangeEvent(
            id="EV-L01",
            previous_clause_version_id="CV-01-old",
            new_clause=clause,
            proposed_rules=(),
            issued_on="2026-04-29",
            effective_on="2026-07-01",
            received_at="2026-10-31T05:00:00Z",
        )


def test_later_layer_endpoints_are_off_by_default(client):
    assert client.get("/api/features").json()["layer1"] is False
    assert (
        client.post("/api/chat", json={"check_id": "CHK-01", "question": "Why?"}).json()["code"]
        == "feature_disabled"
    )
    assert client.get("/api/evaluation").status_code == 404
    assert (
        client.post(
            "/api/legal-changes/EV-01/review", json={"action": "accept", "note": "Reviewed."}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/feedback",
            json={"decision_id": "DEC-01", "phrase": "A phrase", "polarity": "positive"},
        ).status_code
        == 404
    )


def test_layer_fixtures_match_models():
    import json
    from pathlib import Path

    from contracts import models

    root = Path(__file__).resolve().parents[2]
    items = json.loads((root / "data/fixtures/layers.json").read_text())
    for name, item in items.items():
        getattr(models, name).model_validate(item)
