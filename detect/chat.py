"""Narrow citation lookup from an immutable check, without executing record instructions."""

from contracts.models import ChatCitation, ChatRequest, ChatResponse, CheckResult
from detect.validator import validate_findings


def answer(request: ChatRequest, check: CheckResult) -> ChatResponse:
    if request.check_id != check.id:
        return ChatResponse(
            status="needs_evidence", answer="Check snapshot not found.", citations=()
        )
    grounded = validate_findings(
        check.findings, check.snapshot, check.rule_snapshots, check.clause_snapshots
    )
    citations = tuple(
        ChatCitation(
            clause_version_id=f.clause_version_id, quote=f.clause_quote, evidence=f.evidence[0]
        )
        for f in grounded.findings
    )
    return ChatResponse(
        status="answered" if citations else "needs_evidence",
        answer="Review the cited clause and connected evidence with the reviewer."
        if citations
        else "Supporting evidence not found in the connected records.",
        citations=citations,
    )
