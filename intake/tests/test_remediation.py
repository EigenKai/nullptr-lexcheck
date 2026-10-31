"""Task timing policy uses server state; reading never closes a finding."""

import pytest
from fastapi import HTTPException

from intake import service
from intake.fixtures import load_demo
from intake.tests.test_api import post_ok
from intake.tests.test_decisions import fresh_check, payload
from intake.tests.test_decisions import state as state_fixture
from intake.tests.test_runtime import login


@pytest.fixture
def finding(api, monkeypatch):
    monkeypatch.setenv("LEXCHECK_REMEDIATION_ENABLED", "1")
    api.headers["Authorization"] = "Bearer " + login(api)["token"]
    bundle = load_demo()
    post_ok(api, "/api/check", bundle.request.model_dump(mode="json"))
    change = post_ok(api, "/api/changes", bundle.event.model_dump(mode="json"))
    item = next(q for q in change["queue"] if q["target_version_id"] == "RV-02-v1")
    checked = post_ok(api, "/api/rechecks", {"item_id": item["id"], "llm_mode": "off"})
    return (
        api,
        checked,
        {
            "check_id": checked["id"],
            "finding_id": checked["findings"][0]["id"],
            "action": "assign",
            "actor": "reviewer",
            "owner": "marketing",
            "note": "Synthetic task",
            "internal_due_on": "2026-11-01",
            "closure_conditions": "Fresh related deterministic recheck.",
        },
    )


def test_acknowledging_preserves_owner_deadlines_and_assigned_state(finding):
    api, _, plan = finding
    assigned = post_ok(api, "/api/decisions", plan, 201)
    ack = post_ok(
        api,
        "/api/decisions",
        {
            "check_id": plan["check_id"],
            "finding_id": plan["finding_id"],
            "action": "acknowledge",
            "actor": "reviewer",
            "note": "Read by reviewer.",
        },
        201,
    )
    assert ack["task_status"] == "assigned"
    assert ack["request"]["owner"] == "marketing"
    assert ack["request"]["internal_due_on"] == "2026-11-01"
    assert ack["request"]["legal_due_on"] is None
    assert assigned in api.get("/api/history").json()["decisions"]


def test_legal_deadline_requires_the_check_source_and_exact_quote(finding):
    api, checked, plan = finding
    source = checked["clause_snapshots"][0]
    legal = {
        **plan,
        "legal_due_on": "2026-11-02",
        "legal_clause_version_id": source["id"],
        "legal_deadline_quote": "Fabricated source text",
    }
    assert api.post("/api/decisions", json=legal).status_code == 422
    legal["legal_deadline_quote"] = source["text"]
    saved = post_ok(api, "/api/decisions", legal, 201)
    assert saved["request"]["legal_clause_version_id"] == source["id"]


def test_timing_controls_default_off(finding, monkeypatch):
    api, _, plan = finding
    monkeypatch.setenv("LEXCHECK_REMEDIATION_ENABLED", "0")
    assert api.get("/api/features").json()["remediation"] is False
    assert api.post("/api/decisions", json=plan).status_code == 404


def test_assignment_requires_a_date_and_closure_conditions(finding):
    api, _, plan = finding
    del plan["internal_due_on"]
    assert api.post("/api/decisions", json=plan).status_code == 422


def test_closure_conditions_need_human_confirmation_even_after_recheck(tmp_path, monkeypatch):
    monkeypatch.setenv("LEXCHECK_REMEDIATION_ENABLED", "1")
    store, checked, person = state_fixture.__wrapped__(tmp_path)
    service.decide(
        payload(
            checked,
            "assign",
            owner="marketing",
            internal_due_on="2026-11-01",
            closure_conditions="Reviewer checks the correction.",
        ),
        person,
        store,
    )
    fresh = fresh_check(store, checked)
    close = payload(checked, "close", closure_check_id=fresh.id)
    with pytest.raises(HTTPException) as error:
        service.decide(close, person, store)
    assert error.value.status_code == 409
    assert (
        service.decide(
            close.model_copy(update={"closure_conditions_met": True}), person, store
        ).task_status
        == "closed"
    )
