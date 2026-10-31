"""Only proposal fields cross the transport boundary; identity is server-owned."""

from typing import Literal
from uuid import uuid4

from pydantic import Field, ValidationError

from contracts.models import Contract, Evidence, Finding, Id, Text


class Candidate(Contract):
    rule_id: Id
    record_version_id: Id
    clause_quote: Text
    evidence: tuple[Evidence, ...] = Field(min_length=1)


class CandidateBatch(Contract):
    candidates: tuple[Candidate, ...]


class WireEvidence(Contract):
    """Same field constraints as Evidence; cross-field checks run after parsing."""

    record_version_id: Id
    kind: Literal["span", "missing_field", "cell", "page"]
    quote: Text | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=1)
    field: str | None = None
    sheet: str | None = None
    cell: str | None = None
    page: int | None = Field(default=None, ge=1)


class WireCandidate(Contract):
    rule_id: Id
    record_version_id: Id
    clause_quote: Text
    evidence: tuple[WireEvidence, ...] = Field(min_length=1)


class WireCandidateBatch(Contract):
    candidates: tuple[WireCandidate, ...]


def validate_candidates(batch):
    """Drop malformed candidates individually without repairing any evidence."""
    accepted = []
    rejected = 0
    for candidate in batch.candidates:
        try:
            accepted.append(Candidate.model_validate(candidate.model_dump(), strict=True))
        except ValidationError:
            rejected += 1
    return CandidateBatch(candidates=tuple(accepted)), rejected


def materialize(batch, rules):
    index = {rule.id: rule for rule in rules}
    return tuple(
        Finding(
            id="F-" + uuid4().hex,
            rule_id=c.rule_id,
            rule_version=index[c.rule_id].version,
            clause_version_id=index[c.rule_id].clause_version_id,
            record_version_id=c.record_version_id,
            status="suggestion",
            source="llm",
            severity=index[c.rule_id].severity,
            message="Review the cited evidence against this clause.",
            clause_quote=c.clause_quote,
            evidence=c.evidence,
        )
        for c in batch.candidates
        if c.rule_id in index
    )
