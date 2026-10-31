"""Pure legal activation and clean-check impact; all test attestations synthetic."""

from datetime import date, datetime

import pytest

from contracts.models import ClauseVersion, LegalChangeEvent, LegalChangeState, Rule
from intake.fixtures import load_demo
from rules.tests.test_engine import case
from rules.tests.test_impact import prior


@pytest.fixture
def state():
    clause = ClauseVersion(
        id="CV-test-v2",
        clause_id="CL-test",
        document="Synthetic test",
        article="test",
        text="Synthetic test authority requirement",
        source_url="https://example.invalid/test",
        source_sha256="a" * 64,
        retrieved_at="2026-06-01T00:00:00Z",
        valid_from="2026-07-01",
        valid_to="2028-01-01",
        verification_status="verified",
        in_force="in_force",
        verified_by="test-only",
        verified_at="2026-06-02T00:00:00Z",
        status_note="Synthetic only",
    )
    rule = Rule(
        id="R-07",
        version=2,
        clause_version_id=clause.id,
        title="Synthetic authority",
        check_type="authority_review",
        activities=("ad_registration",),
        verification_status="verified",
        enabled=False,
    )
    event = LegalChangeEvent(
        id="LAW-test",
        previous_clause_version_id="CV-test-v1",
        new_clause=clause,
        proposed_rules=(rule,),
        issued_on="2026-04-29",
        effective_on="2026-07-01",
        received_at="2026-06-01T01:00:00Z",
    )
    return LegalChangeState(
        event=event,
        interpretation="accepted",
        status="ready",
        reviewed_by="U-test-only",
        reviewed_at="2026-06-03T00:00:00Z",
    )


def test_pending_interpretation_cannot_activate(state):
    from rules.legal import validate_activation

    for interpretation in ("pending", "rejected"):
        assert (
            validate_activation(
                state.model_copy(update={"interpretation": interpretation}), date(2026, 7, 1)
            )
            == ()
        )


def test_effective_date_boundary(state):
    from rules.legal import validate_activation

    before = state.model_dump_json()
    assert validate_activation(state, date(2026, 6, 30)) == ()
    rules = validate_activation(state, date(2026, 7, 1))
    assert isinstance(rules, tuple) and len(rules) == 1 and rules[0].enabled
    assert rules[0].clause_version_id == state.event.new_clause.id
    assert state.model_dump_json() == before and not state.event.proposed_rules[0].enabled
    assert validate_activation(state, date(2028, 1, 1)) == ()


@pytest.mark.parametrize(
    "change",
    [{"verification_status": "to_be_verified"}, {"in_force": "unknown"}, {"source_sha256": None}],
)
def test_unverified_source_cannot_activate(state, change):
    from rules.legal import validate_activation

    event = state.event.model_copy(
        update={"new_clause": state.event.new_clause.model_copy(update=change)}
    )
    assert validate_activation(state.model_copy(update={"event": event}), date(2026, 7, 1)) == ()


@pytest.mark.parametrize(
    "change",
    [
        {"reviewed_by": None},
        {"reviewed_at": None},
        {"status": "rejected"},
        {"reviewed_at": datetime.fromisoformat("2026-05-01T00:00:00+00:00")},
    ],
)
def test_missing_or_inconsistent_review_cannot_activate(state, change):
    from rules.legal import validate_activation

    assert validate_activation(state.model_copy(update=change), date(2026, 7, 1)) == ()


def old_check(state, *, activity="ad_registration", clause_id="CV-test-v1"):
    request = case().model_copy(
        update={"profile": case().profile.model_copy(update={"activity": activity})}
    )
    old_clause = state.event.new_clause.model_copy(
        update={"id": clause_id, "valid_from": date(2018, 2, 2), "valid_to": date(2026, 7, 1)}
    )
    old_rule = state.event.proposed_rules[0].model_copy(
        update={"version": 1, "clause_version_id": clause_id, "enabled": True}
    )
    return prior(load_demo(), request=request).model_copy(
        update={
            "rules_checked": ("R-07",),
            "rule_snapshots": (old_rule,),
            "clause_snapshots": (old_clause,),
        }
    )


def test_affected_checks_includes_clean_previous_checks_and_deduplicates(state):
    from rules.legal import affected_checks

    check = old_check(state)
    before = check.model_dump_json()
    assert not check.findings
    items = affected_checks(state.event, (check, check))
    assert len(items) == len(check.snapshot.target_version_ids)
    assert {q.target_version_id for q in items} == set(check.snapshot.target_version_ids)
    assert all(
        q.event_id == state.event.id
        and q.previous_check_id == check.id
        and q.reason == "legal_dependency"
        for q in items
    )
    assert items == affected_checks(state.event, (check,))
    assert check.model_dump_json() == before


def test_unrelated_activity_and_clause_are_excluded(state):
    from rules.legal import affected_checks

    assert affected_checks(state.event, (old_check(state, activity="advertising"),)) == ()
    assert affected_checks(state.event, (old_check(state, clause_id="CV-other"),)) == ()


def test_older_confirmation_is_not_declared_void(state):
    from rules.legal import affected_checks

    check = old_check(state)
    before = check.snapshot.versions
    items = affected_checks(state.event, (check,))
    assert items and check.snapshot.versions == before
    assert all(item.status == "queued" and item.new_check_id is None for item in items)


def test_preloaded_update_preserves_history():
    from rules.legal import load_preloaded, validate_activation

    old, state = load_preloaded()
    assert old.id == state.event.previous_clause_version_id == "CV-07-v1"
    assert state.event.new_clause.id == "CV-07-v2"
    assert state.event.issued_on == date(2026, 4, 29)
    assert state.event.effective_on == date(2026, 7, 1)
    assert state.event.received_at.date() == date(2026, 10, 31)
    assert (
        state.reviewed_at is None
        and state.activated_at is None
        and state.interpretation == "pending"
    )
    assert state.event.new_clause.verified_by == old.verified_by == "Dung"
    assert not any(r.enabled for r in state.event.proposed_rules)
    assert validate_activation(state, date(2026, 10, 31)) == ()


def test_previous_clause_matches_original_nd15_article27_5a_verbatim():
    from rules.legal import load_preloaded

    previous, _ = load_preloaded()
    assert previous.text == (
        "Tổ chức, cá nhân có sản phẩm quảng cáo gửi hồ sơ đăng ký xác nhận "
        "nội dung quảng cáo đến cơ quan cấp Giấy tiếp nhận đăng ký bản công bố sản phẩm;"
    )


@pytest.mark.parametrize("change", [{"verification_status": "to_be_verified"}, {"method": "llm"}])
def test_unverified_or_model_rule_does_not_activate(state, change):
    from rules.legal import validate_activation

    rule = state.event.proposed_rules[0].model_copy(update=change)
    event = state.event.model_copy(update={"proposed_rules": (rule,)})
    assert validate_activation(state.model_copy(update={"event": event}), date(2026, 7, 1)) == ()


def test_ambiguous_rule_ids_and_check_ids_are_rejected(state):
    from rules.legal import affected_checks, validate_activation

    event = state.event.model_copy(update={"proposed_rules": state.event.proposed_rules * 2})
    assert validate_activation(state.model_copy(update={"event": event}), date(2026, 7, 1)) == ()
    check = old_check(state)
    with pytest.raises(ValueError):
        affected_checks(
            state.event, (check, check.model_copy(update={"summary": "Different snapshot"}))
        )


@pytest.mark.parametrize("in_force,expected_status", [("unknown", 409), ("in_force", 200)])
def test_intake_activation_handles_owner_result_without_server_error(
    state, tmp_path, monkeypatch, in_force, expected_status
):
    """Route-policy regression with a test-only gate bypass, not layer2 smoke."""
    from fastapi.testclient import TestClient

    from app.main import create_app
    from intake import layer_routes

    monkeypatch.setenv("LEXCHECK_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setattr(layer_routes, "gate", lambda _layer: None)
    clause = state.event.new_clause.model_copy(update={"in_force": in_force})
    event = state.event.model_copy(update={"new_clause": clause})
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        token = client.post("/api/session", json={"user_id": "U-MANAGER"}).json()["token"]
        client.headers["Authorization"] = "Bearer " + token
        assert (
            client.post("/api/legal-changes", json=event.model_dump(mode="json")).status_code == 200
        )
        assert (
            client.post(
                f"/api/legal-changes/{event.id}/review",
                json={"action": "accept", "note": "Synthetic review only"},
            ).status_code
            == 200
        )
        result = client.post(
            f"/api/legal-changes/{event.id}/activate", json={"review_date": "2026-10-31"}
        )
        assert result.status_code == expected_status
