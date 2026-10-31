"""Public development references; never treated as measured or active legal rules."""

import copy
import importlib
import json
from pathlib import Path

import pytest

from contracts.models import CheckRequest, ClauseVersion, Evidence, Rule

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "rules/examples/generation/reference.json"


def reference():
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


def test_examples_are_three_unverified_output_targets_with_real_contracts():
    data = reference()
    assert data["purpose"] == "development_reference_only"
    assert data["model_call_performed"] is False
    assert len(data["examples"]) == 3
    for example in data["examples"]:
        rule = Rule.model_validate(example["expected_rule"])
        clause = ClauseVersion.model_validate(example["expected_clause"])
        assert not rule.enabled
        assert rule.verification_status == clause.verification_status == "to_be_verified"
        assert clause.in_force == "unknown"
        assert clause.verified_by is clause.verified_at is None
        assert rule.clause_version_id == clause.id
        assert clause.text in example["input"]["source_text"]


@pytest.mark.parametrize("check_type", ["warning", "uses", "confirmation"])
def test_each_reference_has_two_positive_and_two_close_negative_cases(check_type):
    example = next(
        e for e in reference()["examples"] if e["expected_rule"]["check_type"] == check_type
    )
    assert sum(c["expected"]["triggered"] for c in example["cases"]) >= 2
    assert sum(not c["expected"]["triggered"] for c in example["cases"]) >= 2
    for case in example["cases"]:
        request = CheckRequest.model_validate(case["input"])
        assert request.profile.synthetic
        assert request.llm_mode == "off"
        expected = case["expected"]
        if expected["triggered"]:
            assert expected["status"] == (
                "needs_review" if check_type == "warning" else "needs_evidence"
            )
        for raw in expected["evidence"]:
            evidence = Evidence.model_validate(raw)
            version = next(v for v in request.versions if v.id == evidence.record_version_id)
            if evidence.kind == "span":
                assert version.text[evidence.start : evidence.end] == evidence.quote
            if evidence.kind == "missing_field":
                assert evidence.quote is None


def test_reference_rules_are_never_in_the_runtime_catalog_or_demo():
    data = reference()
    ids = {e["expected_rule"]["id"] for e in data["examples"]}
    catalog = json.loads((ROOT / "rules/catalog.json").read_text(encoding="utf-8"))
    assert not ids.intersection(r["id"] for r in catalog)
    from intake.fixtures import load_demo
    from rules.engine import evaluate

    result = evaluate(load_demo().request)
    assert not ids.intersection(result.rules_checked)
    assert not ids.intersection(r.id for r in load_demo().rules)


def test_candidate_checker_accepts_different_generated_ids():
    checker = importlib.import_module("rules.example_validation")
    example = reference()["examples"][0]
    candidate = copy.deepcopy(example["expected_rule"])
    candidate["id"] = "GENERATED-77"
    assert checker.validate_candidate(example, candidate) == ()


def test_candidate_checker_rejects_changed_scope_active_state_and_bogus_citation():
    checker = importlib.import_module("rules.example_validation")
    example = reference()["examples"][0]
    candidate = copy.deepcopy(example["expected_rule"])
    candidate.update(activities=["ad_registration"], clause_version_id="CV-INVENTED")
    assert set(checker.validate_candidate(example, candidate)) == {
        "scope_mismatch",
        "unknown_clause",
    }
    candidate = copy.deepcopy(example["expected_rule"])
    candidate.update(enabled=True, verification_status="verified")
    assert "must_remain_candidate" in checker.validate_candidate(example, candidate)


def test_grounding_checker_rejects_invented_quote_and_unicode_offset_drift():
    checker = importlib.import_module("rules.example_validation")
    example = reference()["examples"][0]
    source = example["input"]
    quote = example["source_evidence"]
    assert checker.validate_source_quote(source, quote) == ()
    assert checker.validate_source_quote(source, {**quote, "quote": "Câu tự bịa."})
    assert checker.validate_source_quote(source, {**quote, "start": quote["start"] + 1})


def test_example_checker_does_not_grade_legal_meaning_as_proven():
    checker = importlib.import_module("rules.example_validation")
    report = checker.check_references(reference())
    assert report["example_count"] == 3
    assert report["case_count"] >= 12
    assert report["errors"] == []
    assert report["legal_accuracy_measured"] is False
    assert report["runtime_rules_activated"] == 0
