from datetime import date

from contracts.models import CheckResult
from detect.client import cache_key
from detect.inputs import model_input
from detect.versions import assess_basis, replay_check


def test_old_decision_replays_original_basis(request_data, basis):
    rule, clause, finding = basis
    old = request_data.model_copy(update={"review_date": date(2026, 6, 30)})
    check = CheckResult(
        id="CHK-old",
        mode="live",
        status="needs_review",
        summary="Review",
        rules_checked=(rule.id,),
        skipped_rule_ids=(),
        findings=(finding,),
        snapshot=old,
        model_status="off",
        created_at="2026-06-30T05:00:00Z",
        rule_snapshots=(rule,),
        clause_snapshots=(clause,),
    )
    frozen = check.model_dump_json()
    newer = clause.model_copy(
        update={
            "id": "CV-07-v2",
            "valid_from": date(2026, 7, 1),
            "text": "Updated test-only clause",
        }
    )
    assert assess_basis(request_data, (rule,), (clause, newer)).status == "needs_evidence"
    assert replay_check(check).findings == (finding,)
    assert check.model_dump_json() == frozen


def test_legal_update_invalidates_cache(request_data, basis):
    rule, clause, _ = basis
    before = cache_key(model_input(request_data, (rule,), (clause,)))
    newer = clause.model_copy(
        update={
            "id": "CV-07-v2",
            "valid_from": date(2026, 7, 1),
            "text": "Updated test-only clause",
        }
    )
    assert before != cache_key(model_input(request_data, (rule,), (clause, newer)))
    assert before != cache_key(
        model_input(
            request_data.model_copy(update={"review_date": date(2026, 6, 30)}), (rule,), (clause,)
        )
    )


def test_pending_update_never_reports_ready(request_data, basis):
    rule, clause, finding = basis
    new = clause.model_copy(
        update={
            "id": "CV-07-v2",
            "valid_from": date(2026, 7, 1),
            "verification_status": "to_be_verified",
            "in_force": "unknown",
        }
    )
    state = assess_basis(request_data, (rule,), (clause, new))
    assert state.status == "needs_evidence" and state.pending_clause_ids == (new.id,)
    assert (
        assess_basis(
            request_data.model_copy(update={"review_date": date(2026, 6, 30)}),
            (rule,),
            (clause, new),
        ).status
        == "ready"
    )
    from detect.validator import validate_findings

    assert (
        validate_findings((finding,), request_data, (rule,), (clause, new)).rejected[0].reason
        == "inactive_clause"
    )
