"""Only proposal fields cross the transport boundary; identity is server-owned."""

from uuid import uuid4

from pydantic import Field

from contracts.models import Contract, Evidence, Finding, Id, Text


class Candidate(Contract):
    rule_id: Id
    record_version_id: Id
    clause_quote: Text
    evidence: tuple[Evidence, ...] = Field(min_length=1)


class CandidateBatch(Contract):
    candidates: tuple[Candidate, ...]


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
