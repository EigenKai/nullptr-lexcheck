"""Read-only development cases with injected synthetic basis; no catalog activation."""

import json
from pathlib import Path

import pytest

from contracts.models import CheckRequest, Evidence
from detect.validator import validate_findings
from rules.engine import evaluate

EXAMPLES = json.loads(
    (Path(__file__).resolve().parents[2] / "rules/examples/generation/reference.json").read_text()
)["examples"]
CASES = tuple((example, case) for example in EXAMPLES for case in example["cases"])


def test_reference_double_space_warning_counts_as_present(basis):
    example = next(e for e in EXAMPLES if e["id"] == "EX-WARNING")
    case = next(c for c in example["cases"] if c["id"] == "W-UNICODE")
    request = CheckRequest.model_validate(case["input"])
    text = example["expected_rule"]["negative_examples"][1]
    assert "  " in text
    assert next(v.text for v in request.versions if v.id == "RV-02-v1") == text
    rule, clause, finding = basis
    candidate = finding.model_copy(
        update={
            "evidence": (
                Evidence(record_version_id="RV-02-v1", kind="missing_field", field="warning"),
            )
        }
    )
    result = validate_findings((candidate,), request, (rule,), (clause,))
    assert result.findings == ()
    assert [r.reason for r in result.rejected] == ["missing_field_present"]


@pytest.mark.parametrize("example,case", CASES, ids=[case["id"] for _, case in CASES])
def test_reference_engine_validator_system(basis, example, case):
    assert len(CASES) == 13
    request = CheckRequest.model_validate(case["input"])
    original = request.model_dump_json()
    synthetic_rule, clause, _ = basis
    rule = synthetic_rule.model_copy(update={"check_type": example["expected_rule"]["check_type"]})
    evaluation = evaluate(request, rules=(rule,), clauses=(clause,))
    result = validate_findings(
        evaluation.findings, request, evaluation.rule_snapshots, evaluation.clause_snapshots
    )
    expected = case["expected"]
    # References name the concept; runtime's canonical missing-field key is confirmation_date.
    expected_evidence = tuple(
        Evidence.model_validate(
            {**raw, "field": "confirmation_date"}
            if raw.get("field") == "linked_ad_confirmation"
            else raw
        )
        for raw in expected["evidence"]
    )
    assert evaluation.mode == "live" and evaluation.applicability == "applies"
    assert evaluation.rules_checked == (rule.id,)
    assert result.rejected == ()
    assert result.findings == evaluation.findings
    assert bool(result.findings) is expected["triggered"]
    assert tuple(e for finding in result.findings for e in finding.evidence) == expected_evidence
    assert all(
        finding.status == expected["status"]
        and finding.source == "rule"
        and finding.rule_id == rule.id
        and finding.clause_version_id == clause.id
        for finding in result.findings
    )
    assert request.model_dump_json() == original
