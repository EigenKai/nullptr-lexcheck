"""Human-reviewed, version-scoped positive phrase reuse with labelled dev guards."""

import hashlib
import json
from pathlib import Path

from contracts.models import CheckRequest, Evidence, Pattern

GUARDS = Path(__file__).with_name("examples") / "pattern-guard-labels.json"


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _evidence(pattern, request):
    records = {record.id: record for record in request.records}
    return tuple(
        Evidence(
            record_version_id=version.id,
            kind="span",
            quote=pattern.phrase,
            start=version.text.index(pattern.phrase),
            end=version.text.index(pattern.phrase) + len(pattern.phrase),
        )
        for version in request.versions
        if version.id in request.target_version_ids
        and records[version.record_id].kind in ("marketing", "customer_script")
        and pattern.phrase in version.text
    )


def _scope(pattern, request, rule):
    return (
        pattern.polarity == "positive"
        and rule is not None
        and rule.check_type == "endorsement"
        and pattern.company_id == request.profile.company_id
        and pattern.pack == request.profile.product_group
        and request.profile.confirmed
        and request.profile.activity in rule.activities
        and pattern.rule_id == rule.id
        and pattern.rule_version == rule.version
        and pattern.clause_version_id == rule.clause_version_id
    )


def review(pattern: Pattern, cases: tuple[CheckRequest, ...]) -> Pattern:
    """Review labelled dev guards; caller supplies an authenticated human reviewer.

    Actual confirmed-decision membership/ACL and canonical layer3 gate belong to
    intake. Missing human review never promotes. Labels are explicit development
    annotations, not predictions from a model or an evaluation of held-out data.
    """
    from contracts.models import ClauseVersion, Rule
    from rules import engine

    pattern = Pattern.model_validate(pattern.model_dump(mode="json"))
    if pattern.state != "candidate":
        raise ValueError("Only candidate patterns can be reviewed.")
    if not pattern.reviewed_by:
        return pattern
    labels = json.loads(GUARDS.read_text(encoding="utf-8"))
    fingerprints = [_digest(case.model_dump(mode="json")) for case in cases]
    if len(set(fingerprints)) < 4 or any(key not in labels["cases"] for key in fingerprints):
        raise ValueError(
            "At least four distinct, explicitly labelled development guards are required."
        )
    rules = engine._load("catalog.json", Rule)
    clauses = engine._load("clauses.json", ClauseVersion)
    rule = next((r for r in rules if r.id == pattern.rule_id), None)
    clause = next((c for c in clauses if c.id == pattern.clause_version_id), None)
    scope_keys = ("company_id", "pack", "rule_id", "rule_version", "clause_version_id")
    scope_matches = all(getattr(pattern, key) == labels[key] for key in scope_keys)
    rows = []
    for request, fingerprint in zip(cases, fingerprints):
        expected = set(labels["cases"][fingerprint]["positive_target_ids"])
        eligible = (
            scope_matches
            and _scope(pattern, request, rule)
            and engine._active(rule, clause, clauses, request.review_date)
        )
        actual = {e.record_version_id for e in _evidence(pattern, request)} if eligible else set()
        rows.append(
            {
                "input_sha256": fingerprint,
                "expected": sorted(expected),
                "actual": sorted(actual),
                "false_positive": sorted(actual - expected),
                "missed": sorted(expected - actual),
            }
        )
    positives = sum(bool(row["expected"]) for row in rows)
    clean = sum(not row["expected"] for row in rows)
    passed = (
        scope_matches
        and pattern.polarity == "positive"
        and positives >= 2
        and clean >= 2
        and all(not row["false_positive"] and not row["missed"] for row in rows)
    )
    report = {
        "pattern": pattern.model_dump(mode="json"),
        "guards": rows,
        "passed": passed,
        "source_sha256": clause.source_sha256 if clause else None,
        "label_provenance": labels["provenance"],
    }
    return Pattern.model_validate(
        {
            **pattern.model_dump(mode="json"),
            "state": "active" if passed else "rejected",
            "test_report_sha256": _digest(report),
        }
    )


def apply_patterns(request, rules, findings, patterns):
    """Reuse reviewed phrases on existing evidence, preserving all rule decisions.

    Novel detection expansion is deliberately deferred. Negation and medical
    safety-advice guards from the deterministic check cannot be bypassed by a
    phrase that happened to pass a finite development guard set.
    """
    rule_map = {rule.id: rule for rule in rules}
    result = {finding.id: finding for finding in findings}
    for supplied in sorted(patterns, key=lambda item: item.id):
        pattern = Pattern.model_validate(supplied.model_dump(mode="json"))
        rule = rule_map.get(pattern.rule_id)
        if pattern.state != "active" or not _scope(pattern, request, rule):
            continue
        for identity, finding in tuple(result.items()):
            if (
                finding.rule_id == rule.id
                and finding.pattern_id is None
                and any(
                    evidence.kind == "span" and pattern.phrase in evidence.quote
                    for evidence in finding.evidence
                )
            ):
                result[identity] = finding.model_copy(update={"pattern_id": pattern.id})
    output = tuple(result.values())
    used = tuple(
        sorted({finding.pattern_id for finding in output if finding.pattern_id is not None})
    )
    return output, used
