"""Fail-closed bootstrap adapter; replace in the detection job."""

from contracts.models import (
    CheckRequest,
    ClauseVersion,
    Finding,
    Rule,
    ValidationRejection,
    ValidationResult,
)


def validate_findings(
    findings: tuple[Finding, ...],
    request: CheckRequest,
    rules: tuple[Rule, ...],
    clauses: tuple[ClauseVersion, ...],
) -> ValidationResult:
    return ValidationResult(
        rejected=tuple(
            ValidationRejection(finding_id=f.id, reason="unverified_rule") for f in findings
        )
    )
