"""Source-grounded proposals remain disabled until separate human review."""

import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from contracts.models import ClauseVersion, Contract, Evidence, Rule
from detect.client import configured_client
from rules.example_validation import validate_source_quote

PROMPT_PATH = Path(__file__).resolve().parents[1] / "rules/examples/generation/prompt.md"


class RuleCandidate(Contract):
    rule: Rule
    source_evidence: Evidence


class RuleCandidateBatch(Contract):
    candidates: tuple[RuleCandidate, ...]


class RuleProposals(Contract):
    mode: Literal["live", "cached", "unavailable"]
    proposals: tuple[Rule, ...] = ()
    source_evidence: tuple[Evidence, ...] = ()
    structurally_valid: int = 0
    rejected: int = 0
    cache_key: str | None = None


def propose_rules(clause: ClauseVersion, *, client=None) -> RuleProposals:
    mode = os.getenv("LEXCHECK_LLM_MODE", "off")
    if mode == "off":
        return RuleProposals(mode="unavailable")
    prompt = (
        PROMPT_PATH.read_text()
        + "\nReturn candidates containing Rule and source_evidence. The supplied clause is fixed; use its ID as clause_version_id and evidence.record_version_id. IDs are placeholders replaced by the server. No activation or legal verification is permitted."
    )
    output = (client or configured_client()).generate(
        purpose="rulegen-v1",
        payload={"clause": clause.model_dump(mode="json")},
        prompt=prompt,
        schema=RuleCandidateBatch,
        mode=mode,
    )
    if output.parsed is None:
        return RuleProposals(mode="unavailable", cache_key=output.key)
    source = {"source_id": clause.id, "source_text": clause.text}
    candidates = output.parsed.candidates
    grounded = tuple(
        c
        for c in candidates
        if c.rule.clause_version_id == clause.id
        and not validate_source_quote(source, c.source_evidence.model_dump(mode="json"))
    )
    rules = tuple(
        Rule.model_validate(
            {
                **c.rule.model_dump(),
                "id": "R-" + uuid4().hex,
                "version": 1,
                "enabled": False,
                "verification_status": "to_be_verified",
            }
        )
        for c in grounded
    )
    return RuleProposals(
        mode=output.status,
        proposals=rules,
        source_evidence=tuple(c.source_evidence for c in grounded),
        structurally_valid=len(candidates),
        rejected=len(candidates) - len(grounded),
        cache_key=output.key,
    )
