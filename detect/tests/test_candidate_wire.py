"""Wire parsing preserves malformed proposals for isolated strict rejection."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from contracts.models import Evidence, RuleEvaluation
from detect.client import ModelClient
from detect.service import suggest_with_trace


def _run(request, basis, count, all_invalid=False):
    rule, clause, finding = basis
    valid = {
        "rule_id": rule.id,
        "record_version_id": finding.record_version_id,
        "clause_quote": clause.text,
        "evidence": [e.model_dump() for e in finding.evidence],
    }
    invalid = {**valid, "evidence": [{**valid["evidence"][0], "field": "warning"}]}
    raw = {"candidates": ([valid] if not all_invalid else []) + [invalid] * count}

    def transport(**kwargs):
        return SimpleNamespace(
            status="completed", output_parsed=kwargs["text_format"].model_validate(raw)
        )

    evaluation = RuleEvaluation(
        mode="live",
        applicability="applies",
        reason="Test",
        rule_snapshots=(rule,),
        clause_snapshots=(clause,),
    )
    return suggest_with_trace(
        request.model_copy(update={"llm_mode": "live"}),
        evaluation,
        client=ModelClient(model="test", transport=transport),
    )


def test_wire_keeps_valid_candidate_and_counts_invalid(request_data, basis):
    trace = _run(request_data, basis, 1)
    assert trace.result.model_status == "live"
    assert len(trace.result.findings) == 1
    assert dict(trace.rejected) == {"schema_invalid": 1}
    assert trace.calls == 1 and trace.error is None


def test_wire_all_invalid_is_live_empty_batch(request_data, basis):
    trace = _run(request_data, basis, 3, all_invalid=True)
    assert trace.result.model_status == "live"
    assert trace.result.findings == ()
    assert dict(trace.rejected) == {"schema_invalid": 3}
    assert trace.calls == 1 and trace.error is None


def test_client_validation_error_has_distinct_code():
    from detect.candidates import CandidateBatch

    def transport(**kwargs):
        return CandidateBatch.model_validate({"candidates": "bad"})

    output = ModelClient(model="test", transport=transport).generate(
        purpose="test", payload={}, prompt="test", schema=CandidateBatch, mode="live"
    )
    assert output.error == "schema_invalid" and output.status == "unavailable"
    assert output.calls == 1


def test_wire_fields_match_strict_contract_without_relaxing_it():
    from detect.candidates import WireEvidence

    assert WireEvidence.model_fields.keys() == Evidence.model_fields.keys()
    for name in Evidence.model_fields:
        assert WireEvidence.model_fields[name].annotation == Evidence.model_fields[name].annotation
    raw = {
        "record_version_id": "RV-01",
        "kind": "span",
        "quote": "text",
        "start": 0,
        "end": 4,
        "field": "warning",
        "sheet": "sheet",
        "cell": "A1",
        "page": 1,
    }
    assert WireEvidence.model_validate(raw).model_dump() == raw
    with pytest.raises(ValidationError, match="span has only offsets"):
        Evidence.model_validate(raw)
