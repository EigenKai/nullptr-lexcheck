"""Pinned official-source metadata after Dung's explicit human confirmation."""

import json
from pathlib import Path

from contracts.models import ClauseVersion, Rule

ROOT = Path(__file__).parents[1]


def catalog():
    return tuple(
        Rule.model_validate(item)
        for item in json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    )


def clauses():
    return {
        item["id"]: ClauseVersion.model_validate(item)
        for item in json.loads((ROOT / "clauses.json").read_text(encoding="utf-8"))
    }


def test_all_enabled_rules_have_verified_basis():
    rules, basis = catalog(), clauses()
    assert {rule.id for rule in rules if rule.enabled} == {"R-01", "R-02", "R-03", "R-04"}
    for rule in rules:
        if not rule.enabled:
            continue
        clause = basis[rule.clause_version_id]
        assert rule.verification_status == clause.verification_status == "verified"
        assert clause.verified_by == "Dung" and clause.verified_at is not None
        assert clause.in_force == "in_force"
        assert (
            clause.source_sha256
            == "a6435d8e778117111bb165d52badb125b7afbe2430334b0f53ec0ea42a3c1ea5"
        )
        assert len(rule.positive_examples) >= 2 and len(rule.negative_examples) >= 2
        assert "PDF" in clause.status_note and "Human" in clause.status_note


def test_catalog_contains_confirmed_excerpts_without_activating_example_ids():
    examples = json.loads(
        (ROOT / "examples/generation/reference.json").read_text(encoding="utf-8")
    )["examples"]
    basis = clauses()
    for number, example in enumerate(examples, 1):
        clause = basis[f"CV-0{number}-v1"]
        assert clause.text == example["expected_clause"]["text"]
        assert clause.article == example["expected_clause"]["article"]
        assert clause.valid_from.isoformat() == "2018-02-02"
        assert "PENDING VERIFICATION" not in clause.text
    assert all(not rule.id.startswith("EX-") for rule in catalog())
    # Reference outputs keep their original development-only state/provenance.
    assert all(not example["input"]["human_verified"] for example in examples)


def test_effective_interval_boundaries():
    from datetime import date

    for key in ("CV-01-v1", "CV-02-v1", "CV-03-v1"):
        clause = clauses()[key]
        assert date(2018, 2, 1) < clause.valid_from
        assert clause.valid_from == date(2018, 2, 2)
        assert clause.valid_from <= date(2026, 10, 31)
        assert clause.valid_to is None


def test_other_pending_rules_and_clauses_remain_disabled():
    for rule in catalog():
        if rule.id not in ("R-01", "R-02", "R-03", "R-04"):
            assert not rule.enabled
            assert rule.verification_status == "to_be_verified"
            assert clauses()[rule.clause_version_id].verification_status == "to_be_verified"
