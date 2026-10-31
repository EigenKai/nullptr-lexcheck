"""Synthetic guard labels and reviewer IDs; no live Pattern is promoted here."""

import json
from pathlib import Path

import pytest

from contracts.models import CheckRequest, Pattern
from detect.validator import validate_findings
from rules.engine import evaluate


@pytest.fixture
def cases():
    return tuple(
        CheckRequest.model_validate(v)
        for v in json.loads(
            (Path(__file__).parents[1] / "examples/pattern-guard.json").read_text(encoding="utf-8")
        )
    )


@pytest.fixture
def pattern():
    return Pattern(
        id="PAT-test",
        company_id="CO-DEMO",
        source_decision_id="DEC-test-only",
        rule_id="R-04",
        rule_version=1,
        clause_version_id="CV-04-v1",
        phrase="bác sĩ An khuyên dùng",
        polarity="positive",
        reviewed_by="U-test-only",
    )


def test_candidate_does_not_change_results(pattern, cases):
    assert evaluate(cases[0], patterns=(pattern,)) == evaluate(cases[0])


def test_clean_guard_blocks_promotion(pattern, cases):
    from rules.patterns import review

    result = review(pattern.model_copy(update={"phrase": "bác sĩ An"}), cases)
    assert result.state == "rejected" and result.test_report_sha256


def test_promoted_pattern_reuses_feedback(pattern, cases, monkeypatch):
    import socket

    from rules.patterns import review

    def forbidden(*args, **kwargs):
        raise AssertionError("Pattern reuse must not access the network")

    monkeypatch.setattr(socket, "socket", forbidden)
    active = review(pattern, cases)
    assert (
        active.state == "active"
        and active.reviewed_by == "U-test-only"
        and active.test_report_sha256
    )
    before = cases[0].model_dump_json()
    result = evaluate(cases[0], patterns=(active,))
    assert result.pattern_ids_used == (active.id,)
    assert result.rules_checked == ("R-01", "R-02", "R-03", "R-04")
    assert any(f.pattern_id == active.id and f.status == "needs_review" for f in result.findings)
    validated = validate_findings(
        result.findings, cases[0], result.rule_snapshots, result.clause_snapshots
    )
    assert validated.rejected == ()
    assert cases[0].model_dump_json() == before
    assert pattern.state == "candidate"


def test_review_requires_human_reviewer(pattern, cases):
    from rules.patterns import review

    result = review(pattern.model_copy(update={"reviewed_by": None}), cases)
    assert result.state == "candidate" and not result.test_report_sha256


def test_legal_version_change_suspends_pattern(pattern, cases):
    from rules.patterns import review

    active = review(pattern, cases)
    result = evaluate(cases[0])
    clause = next(c for c in result.clause_snapshots if c.id == active.clause_version_id)
    new_clause = clause.model_copy(update={"id": "CV-test-new"})
    new_rules = tuple(
        r.model_copy(update={"version": 2, "clause_version_id": new_clause.id})
        if r.id == active.rule_id
        else r
        for r in result.rule_snapshots
    )
    new_clauses = tuple(new_clause if c.id == clause.id else c for c in result.clause_snapshots)
    rechecked = evaluate(cases[0], rules=new_rules, clauses=new_clauses, patterns=(active,))
    assert rechecked.pattern_ids_used == ()
    assert all(f.pattern_id is None for f in rechecked.findings)
    assert active.state == "active"  # pure evaluation never rewrites persisted history


def test_pattern_never_crosses_company(pattern, cases):
    from rules.patterns import review

    active = review(pattern, cases)
    request = cases[0].model_copy(
        update={
            "profile": cases[0].profile.model_copy(update={"company_id": "CO-other"}),
            "records": tuple(
                r.model_copy(update={"company_id": "CO-other"}) for r in cases[0].records
            ),
        }
    )
    assert evaluate(request, patterns=(active,)).pattern_ids_used == ()


def test_negative_patterns_cannot_suppress_rules(pattern, cases):
    from rules.patterns import review

    negative = pattern.model_copy(update={"polarity": "negative"})
    assert review(negative, cases).state == "rejected"
    fake_active = negative.model_copy(update={"state": "active", "test_report_sha256": "0" * 64})
    assert evaluate(cases[0], patterns=(fake_active,)) == evaluate(cases[0])


def test_unknown_or_insufficient_guard_cases_are_refused(pattern, cases):
    from rules.patterns import review

    with pytest.raises(ValueError):
        review(pattern, cases[:3])
    changed = cases[0].model_copy(update={"review_date": cases[0].review_date.replace(day=30)})
    with pytest.raises(ValueError):
        review(pattern, (changed, *cases[1:]))


def test_pattern_does_not_turn_negated_medical_text_into_a_finding(pattern, cases):
    from rules.patterns import review
    from rules.tests.test_engine import change_version

    active = review(pattern, cases)
    target = next(v for v in cases[2].versions if v.id == "RV-02-v1")
    request = change_version(
        cases[2], text=target.text + " Không có bác sĩ An khuyên dùng sản phẩm."
    )
    assert evaluate(request, patterns=(active,)) == evaluate(request)
