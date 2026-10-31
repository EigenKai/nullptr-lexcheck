"""Opt-in checks for development references, never imported by the runtime engine.

These checks assess structure and source grounding, not legal interpretation or
whether a generated rule actually behaves correctly on the example cases.
"""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from contracts.models import CheckRequest, ClauseVersion, Evidence, Rule


def validate_candidate(example: dict, candidate: dict) -> tuple[str, ...]:
    """Compare a generated candidate without requiring a handwritten rule ID."""
    try:
        rule = Rule.model_validate(candidate)
    except ValidationError:
        return ("invalid_rule_contract",)
    expected = Rule.model_validate(example["expected_rule"])
    errors = []
    if rule.enabled or rule.verification_status != "to_be_verified":
        errors.append("must_remain_candidate")
    if rule.clause_version_id != expected.clause_version_id:
        errors.append("unknown_clause")
    if set(rule.activities) != set(expected.activities):
        errors.append("scope_mismatch")
    if rule.check_type != expected.check_type:
        errors.append("check_type_mismatch")
    return tuple(errors)


def validate_source_quote(source: dict, evidence: dict) -> tuple[str, ...]:
    try:
        span = Evidence.model_validate(evidence)
    except ValidationError:
        return ("invalid_evidence_contract",)
    if span.kind != "span" or span.record_version_id != source["source_id"]:
        return ("wrong_source",)
    text = source["source_text"]
    if span.end > len(text) or text[span.start : span.end] != span.quote:
        return ("quote_mismatch",)
    return ()


def check_references(data: dict) -> dict:
    errors = []
    count = 0
    for example in data["examples"]:
        errors.extend(
            f"{example['id']}:{e}" for e in validate_candidate(example, example["expected_rule"])
        )
        clause = ClauseVersion.model_validate(example["expected_clause"])
        if clause.verification_status != "to_be_verified" or clause.in_force != "unknown":
            errors.append(f"{example['id']}:source_not_marked_pending")
        if clause.text not in example["input"]["source_text"]:
            errors.append(f"{example['id']}:clause_quote_mismatch")
        errors.extend(
            f"{example['id']}:{e}"
            for e in validate_source_quote(example["input"], example["source_evidence"])
        )
        for case in example["cases"]:
            request = CheckRequest.model_validate(case["input"])
            versions = {v.id: v for v in request.versions}
            count += 1
            for raw in case["expected"]["evidence"]:
                evidence = Evidence.model_validate(raw)
                if evidence.record_version_id not in versions:
                    errors.append(f"{case['id']}:unknown_record")
                elif evidence.kind == "span":
                    text = versions[evidence.record_version_id].text
                    if text[evidence.start : evidence.end] != evidence.quote:
                        errors.append(f"{case['id']}:record_quote_mismatch")
    return {
        "purpose": "development_reference_check",
        "example_count": len(data["examples"]),
        "case_count": count,
        "errors": errors,
        "legal_accuracy_measured": False,
        "runtime_rules_activated": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    report = check_references(json.loads(args.reference.read_text(encoding="utf-8")))
    print(json.dumps(report, ensure_ascii=False))
    return bool(report["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
