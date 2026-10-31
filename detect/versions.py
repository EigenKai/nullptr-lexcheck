"""Snapshot-only version checks; pending clauses must be supplied by the caller."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BasisAssessment:
    status: str
    pending_clause_ids: tuple[str, ...] = ()


def assess_basis(request, rules, clauses):
    effective = tuple(
        c
        for c in clauses
        if c.valid_from <= request.review_date
        and (c.valid_to is None or request.review_date < c.valid_to)
    )
    latest = tuple(
        c
        for c in effective
        if not any(
            other.clause_id == c.clause_id and other.valid_from > c.valid_from
            for other in effective
        )
    )
    active = {
        r.clause_version_id for r in rules if r.enabled and r.verification_status == "verified"
    }
    pending = tuple(
        sorted(
            c.id
            for c in latest
            if c.id not in active or c.verification_status != "verified" or c.in_force != "in_force"
        )
    )
    return BasisAssessment("needs_evidence" if pending else "ready", pending)


def replay_check(check):
    from detect.validator import validate_findings

    return validate_findings(
        check.findings, check.snapshot, check.rule_snapshots, check.clause_snapshots
    )
