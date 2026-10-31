"""Developer reference cases over injected synthetic basis, never an active catalog."""

import json
from pathlib import Path

import pytest

from contracts.models import CheckRequest, ClauseVersion, Rule
from rules.engine import evaluate

ROOT = Path(__file__).parents[1]
EXAMPLES = json.loads((ROOT / "examples/generation/reference.json").read_text(encoding="utf-8"))[
    "examples"
]
CASES = [(index, case) for index, example in enumerate(EXAMPLES) for case in example["cases"]]


@pytest.mark.parametrize("index,case", CASES, ids=[case["id"] for _, case in CASES])
def test_reference_positive_and_close_negative(index, case):
    example = EXAMPLES[index]
    rule = Rule.model_validate(
        {**example["expected_rule"], "enabled": True, "verification_status": "verified"}
    )
    clause = ClauseVersion.model_validate(
        {
            **example["expected_clause"],
            "text": "Synthetic basis for regression testing only.",
            "source_url": "https://example.invalid/test-only",
            "source_sha256": "0" * 64,
            "verification_status": "verified",
            "in_force": "in_force",
            "verified_by": "synthetic-test-only",
            "verified_at": "2026-10-31T05:00:00Z",
            "status_note": "Synthetic injected basis, not legal source verification.",
        }
    )
    request = CheckRequest.model_validate(case["input"])
    before = request.model_dump_json()
    result = evaluate(request, rules=(rule,), clauses=(clause,))
    assert result.rules_checked == (rule.id,)
    assert bool(result.findings) == case["expected"]["triggered"]
    if result.findings:
        assert all(finding.status == case["expected"]["status"] for finding in result.findings)
        assert all(finding.clause_quote == clause.text for finding in result.findings)
        for finding in result.findings:
            for evidence in finding.evidence:
                if evidence.kind == "span":
                    version = next(
                        v for v in request.versions if v.id == evidence.record_version_id
                    )
                    assert version.text[evidence.start : evidence.end] == evidence.quote
    assert request.model_dump_json() == before


def test_disabled_and_out_of_activity_rules_are_not_reported_as_skipped():
    example = EXAMPLES[0]
    rule = Rule.model_validate(
        {**example["expected_rule"], "enabled": True, "verification_status": "verified"}
    )
    clause = ClauseVersion.model_validate(
        {
            **example["expected_clause"],
            "text": "Synthetic basis only.",
            "source_url": "https://example.invalid/synthetic",
            "source_sha256": "0" * 64,
            "verification_status": "verified",
            "in_force": "in_force",
            "verified_by": "synthetic-test-only",
            "verified_at": "2026-10-31T05:00:00Z",
            "status_note": "Synthetic basis only.",
        }
    )
    disabled = rule.model_copy(update={"id": "TEST-disabled", "enabled": False})
    out_of_scope = rule.model_copy(
        update={"id": "TEST-registration", "activities": ("ad_registration",)}
    )
    request = CheckRequest.model_validate(example["cases"][2]["input"])
    result = evaluate(request, rules=(rule, disabled, out_of_scope), clauses=(clause,))
    assert result.rules_checked == (rule.id,)
    assert result.skipped_rule_ids == ()
