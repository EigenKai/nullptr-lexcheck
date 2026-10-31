"""Ground findings against the exact supplied snapshot, without text normalization."""

from contracts.models import (
    CheckRequest,
    ClauseVersion,
    Finding,
    Rule,
    ValidationRejection,
    ValidationResult,
)

WARNING = "Thực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh."
# Closed field map: structured fields use presence; warning is an exact text substring.
FIELD_PRESENT = {
    "uses": lambda v: bool(v.uses),
    "reference_ids": lambda v: bool(v.reference_ids),
    "confirmation_date": lambda v: v.confirmation_date is not None,
    "issuing_authority": lambda v: v.issuing_authority != "unknown",
    "warning": lambda v: WARNING in v.text,
    "text": lambda v: bool(v.text.strip()),
}


def _reason(finding, request, rules, clauses):
    rule = rules.get(finding.rule_id)
    if rule is None:
        return "unknown_rule"
    if (
        not rule.enabled
        or rule.verification_status != "verified"
        or finding.rule_version != rule.version
    ):
        return "unverified_rule"
    clause = clauses.get(finding.clause_version_id)
    if clause is None or rule.clause_version_id != clause.id:
        return "unknown_clause"
    if (
        clause.verification_status != "verified"
        or clause.in_force != "in_force"
        or request.review_date < clause.valid_from
        or (clause.valid_to is not None and request.review_date >= clause.valid_to)
    ):
        return "inactive_clause"
    if not finding.clause_quote or finding.clause_quote not in clause.text:
        return "quote_mismatch"
    selected = set(request.target_version_ids + request.context_version_ids)
    versions = {v.id: v for v in request.versions if v.id in selected}
    if finding.record_version_id not in versions or not finding.evidence:
        return "evidence_mismatch"
    if finding.source == "llm" and finding.status not in ("suggestion", "needs_evidence"):
        return "evidence_mismatch"
    for evidence in finding.evidence:
        version = versions.get(evidence.record_version_id)
        if version is None:
            return "evidence_mismatch"
        if evidence.kind == "span":
            if (
                evidence.start is None
                or evidence.end is None
                or evidence.start < 0
                or evidence.end <= evidence.start
                or evidence.end > len(version.text)
                or version.text[evidence.start : evidence.end] != evidence.quote
            ):
                return "evidence_mismatch"
        elif evidence.kind != "missing_field" or evidence.field not in FIELD_PRESENT:
            # RecordVersion has no authoritative cell/page map.
            return "evidence_mismatch"
        elif evidence.quote is not None:
            return "evidence_mismatch"
    if any(
        e.kind == "missing_field" and any(FIELD_PRESENT[e.field](v) for v in versions.values())
        for e in finding.evidence
    ):
        return "missing_field_present"
    return None


def validate_findings(
    findings: tuple[Finding, ...],
    request: CheckRequest,
    rules: tuple[Rule, ...],
    clauses: tuple[ClauseVersion, ...],
) -> ValidationResult:
    """First failure wins: rule ID, rule activation/version, clause ID, clause
    activity/date, clause quote, evidence membership/location, field presence.
    Both sources follow the same checks; accepted findings retain identity.
    """
    rule_map = {r.id: r for r in rules}
    clause_map = {c.id: c for c in clauses}
    results = tuple((f, _reason(f, request, rule_map, clause_map)) for f in findings)
    return ValidationResult(
        findings=tuple(f for f, reason in results if reason is None),
        rejected=tuple(
            ValidationRejection(finding_id=f.id, reason=reason)
            for f, reason in results
            if reason is not None
        ),
    )
