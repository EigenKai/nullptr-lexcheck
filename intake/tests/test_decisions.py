"""State-policy unit tests with synthetic snapshots; these do not test a legal engine."""

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

from contracts.models import CheckResult, DecisionRequest
from intake import auth, service
from intake.fixtures import load_demo
from intake.store import State, Store


@pytest.fixture
def state(tmp_path):
    store = Store(tmp_path / "state.json")
    result = CheckResult.model_validate_json(
        Path("data/fixtures/finding-preview.json").read_text(encoding="utf-8")
    )
    store.data = State()  # Isolated unit snapshot, not the deployed demo.
    store.save_check(result)
    return store, result, auth.Principal("U-MANAGER", "manager", auth.now() + timedelta(hours=1))


def payload(check, action="confirm", **extra):
    return DecisionRequest(
        check_id=check.id,
        finding_id=check.findings[0].id,
        action=action,
        actor="reviewer",
        note="Synthetic policy test",
        **extra,
    )


def test_assignment_does_not_close_task(state):
    store, check, person = state
    result = service.decide(payload(check, "assign", owner="marketing"), person, store)
    assert result.task_status == "assigned"
    assert result.actor_user_id == "U-MANAGER"
    assert store.checks[check.id] == check


def test_confirm_is_not_closure(state):
    store, check, person = state
    assert service.decide(payload(check), person, store).task_status == "open"


def test_closure_rejects_a_missing_or_unrelated_check(state):
    store, check, person = state
    with pytest.raises(HTTPException) as exc:
        service.decide(payload(check, "close", closure_check_id="CHK-absent"), person, store)
    assert exc.value.status_code == 409
    assert store.decisions == {}


def test_whitespace_note_is_not_a_review(state):
    store, check, person = state
    with pytest.raises(HTTPException) as exc:
        service.decide(payload(check).model_copy(update={"note": "   "}), person, store)
    assert exc.value.status_code == 422


def test_dismissed_task_cannot_be_reopened_by_assignment(state):
    store, check, person = state
    service.decide(payload(check, "reject"), person, store)
    with pytest.raises(HTTPException) as exc:
        service.decide(payload(check, "assign", owner="marketing"), person, store)
    assert exc.value.status_code == 409


def fresh_check(store, check):
    """Synthetic completed checker output for state-policy tests, not a measured result."""
    finding = check.findings[0]
    bundle = load_demo()
    rule = next(r for r in bundle.rules if r.id == finding.rule_id)
    clause = next(c for c in bundle.clauses if c.id == finding.clause_version_id)
    data = check.model_dump(mode="json")
    data.update(
        id="CHK-STATE-FRESH",
        mode="live",
        status="no_issue_found",
        summary="no issue found under 1 encoded rules",
        findings=[],
        rules_checked=[rule.id],
        skipped_rule_ids=[],
        rule_snapshots=[rule.model_dump(mode="json")],
        clause_snapshots=[clause.model_dump(mode="json")],
        parent_check_id=check.id,
        applicability="applies",
        created_at=auth.now().isoformat(),
    )
    fresh = CheckResult.model_validate(data)
    store.save_check(fresh)
    return fresh


def test_closure_accepts_only_a_fresh_related_check(state):
    store, check, person = state
    fresh = fresh_check(store, check)
    response = service.decide(payload(check, "close", closure_check_id=fresh.id), person, store)
    assert response.task_status == "closed"
    assert store.checks[check.id] == check


def test_newer_record_prevents_closure_with_a_stale_recheck(state):
    store, check, person = state
    fresh = fresh_check(store, check)
    target = next(v for v in check.snapshot.versions if v.id == check.findings[0].record_version_id)
    updated = target.model_copy(
        update={"id": "RV-STATE-NEW", "version": target.version + 1, "supersedes": target.id}
    )
    with store.transaction():
        store.versions[updated.id] = updated
    with pytest.raises(HTTPException) as exc:
        service.decide(payload(check, "close", closure_check_id=fresh.id), person, store)
    assert exc.value.status_code == 409


def test_duplicate_event_is_idempotent_without_replaying_impact(state):
    store, _, _ = state
    event = load_demo().event
    with store.transaction():
        store.events[event.id] = event
    assert service.change(event, store) == ()
    with pytest.raises(HTTPException) as exc:
        service.change(event.model_copy(update={"record_id": "REC-DIFFERENT"}), store)
    assert exc.value.status_code == 409


def test_missing_impact_owner_does_not_mutate_state(state, monkeypatch):
    def missing(_name):
        raise HTTPException(503, "not_ready")

    monkeypatch.setattr(service, "owner_module", missing)
    store, _, _ = state
    before = store.data.model_copy(deep=True)
    with pytest.raises(HTTPException) as exc:
        service.change(load_demo().event, store)
    assert exc.value.status_code == 503
    assert store.data == before
