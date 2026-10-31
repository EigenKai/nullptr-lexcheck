import pytest

from contracts.models import RuleEvaluation
from detect.candidates import CandidateBatch
from detect.client import ModelClient, cache_key
from detect.service import suggest


def test_cache_key_changes_with_clause():
    assert cache_key({"clause": "v1"}) != cache_key({"clause": "v2"})


def test_timeout_preserves_rule_result(request_data, basis, monkeypatch):
    rule, clause, finding = basis
    evaluation = RuleEvaluation(
        mode="live",
        applicability="applies",
        reason="Test",
        findings=(finding,),
        rule_snapshots=(rule,),
        clause_snapshots=(clause,),
    )

    def timeout(**kwargs):
        raise TimeoutError()

    client = ModelClient(transport=timeout, model="test", cache_dir=None)
    result = suggest(
        request_data.model_copy(update={"llm_mode": "live"}), evaluation, client=client
    )
    assert result.model_status == "unavailable"
    assert evaluation.findings == (finding,)


@pytest.mark.parametrize("mode", ["off", "cache"])
def test_no_network_modes(mode, tmp_path):
    def forbidden(**kwargs):
        raise AssertionError("network")

    client = ModelClient(transport=forbidden, model="test", cache_dir=tmp_path)
    result = client.generate(
        purpose="test", payload={}, prompt="test", schema=CandidateBatch, mode=mode
    )
    assert result.status in ("off", "unavailable")
    assert not list(tmp_path.iterdir())


def test_real_output_cache_roundtrip(tmp_path):
    from types import SimpleNamespace

    calls = []

    def transport(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_parsed=CandidateBatch(candidates=()))

    client = ModelClient(
        transport=transport,
        model="test",
        cache_dir=tmp_path,
        user_id="U-test",
        group="manager",
        acl_hash="acl",
    )
    args = {"purpose": "test", "payload": {}, "prompt": "test", "schema": CandidateBatch}
    assert client.generate(**args, mode="live").status == "live"
    assert client.generate(**args, mode="cache").status == "cached"
    assert len(calls) == 1
    assert calls[0]["text_format"] is CandidateBatch


@pytest.mark.parametrize("status,parsed", [("incomplete", None), ("completed", None)])
def test_refusal_and_incomplete(status, parsed):
    from types import SimpleNamespace

    client = ModelClient(
        transport=lambda **kw: SimpleNamespace(status=status, output_parsed=parsed), model="test"
    )
    assert (
        client.generate(
            purpose="test", payload={}, prompt="test", schema=CandidateBatch, mode="live"
        ).status
        == "unavailable"
    )


def test_transport_proposals_are_grounded(request_data, basis):
    from types import SimpleNamespace

    from detect.candidates import Candidate

    rule, clause, finding = basis
    evaluation = RuleEvaluation(
        mode="live",
        applicability="applies",
        reason="Test",
        rule_snapshots=(rule,),
        clause_snapshots=(clause,),
    )
    candidate = Candidate(
        rule_id=rule.id,
        record_version_id=finding.record_version_id,
        clause_quote=clause.text,
        evidence=finding.evidence,
    )
    client = ModelClient(
        model="test",
        transport=lambda **kw: SimpleNamespace(
            status="completed", output_parsed=CandidateBatch(candidates=(candidate,))
        ),
    )
    result = suggest(
        request_data.model_copy(update={"llm_mode": "live"}), evaluation, client=client
    )
    assert len(result.findings) == 1
    assert result.findings[0].source == "llm" and result.findings[0].status == "suggestion"
    assert result.findings[0].id != finding.id


def test_invalid_cache_is_unavailable(tmp_path):
    from types import SimpleNamespace

    client = ModelClient(
        model="test",
        cache_dir=tmp_path,
        user_id="U-test",
        group="manager",
        acl_hash="acl",
        transport=lambda **kw: SimpleNamespace(
            status="completed", output_parsed=CandidateBatch(candidates=())
        ),
    )
    args = {"purpose": "test", "payload": {}, "prompt": "test", "schema": CandidateBatch}
    result = client.generate(**args, mode="live")
    (tmp_path / (result.key + ".json")).write_text("{bad")
    assert client.generate(**args, mode="cache").error == "cache_invalid"


def test_no_credentials_no_call(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = ModelClient(model="test")
    result = client.generate(
        purpose="test", payload={}, prompt="test", schema=CandidateBatch, mode="live"
    )
    assert result.calls == 0 and result.status == "unavailable"


def test_rejections_counted(request_data, basis):
    from types import SimpleNamespace

    from detect.candidates import Candidate
    from detect.service import suggest_with_trace

    rule, clause, finding = basis
    candidate = Candidate(
        rule_id="R-absent",
        record_version_id=finding.record_version_id,
        clause_quote=clause.text,
        evidence=finding.evidence,
    )
    client = ModelClient(
        model="test",
        transport=lambda **kw: SimpleNamespace(
            status="completed", output_parsed=CandidateBatch(candidates=(candidate,))
        ),
    )
    evaluation = RuleEvaluation(
        mode="live",
        applicability="applies",
        reason="Test",
        rule_snapshots=(rule,),
        clause_snapshots=(clause,),
    )
    trace = suggest_with_trace(
        request_data.model_copy(update={"llm_mode": "live"}), evaluation, client=client
    )
    assert dict(trace.rejected) == {"unknown_rule": 1}
    assert not trace.result.findings


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 60),
        ("30.5", 30.5),
        ("180", 180),
        ("0", 60),
        ("-1", 60),
        ("181", 60),
        ("bad", 60),
        ("nan", 60),
        ("inf", 60),
    ],
)
def test_timeout_from_env_with_bounds(monkeypatch, value, expected):
    from detect.client import timeout_seconds

    if value is None:
        monkeypatch.delenv("LEXCHECK_LLM_TIMEOUT_SECONDS", raising=False)
    else:
        monkeypatch.setenv("LEXCHECK_LLM_TIMEOUT_SECONDS", value)
    assert timeout_seconds() == expected


def test_timeout_error_code_is_distinct(request_data, basis):
    import importlib

    import httpx

    sdk = importlib.import_module("openai")

    def timeout(**kwargs):
        raise sdk.APITimeoutError(request=httpx.Request("POST", "https://example.org"))

    client = ModelClient(transport=timeout, model="test")
    output = client.generate(
        purpose="test", payload={}, prompt="test", schema=CandidateBatch, mode="live"
    )
    assert output.error == "timeout" and output.calls == 1
    rule, clause, finding = basis
    evaluation = RuleEvaluation(
        mode="live",
        applicability="applies",
        reason="Test",
        findings=(finding,),
        rule_snapshots=(rule,),
        clause_snapshots=(clause,),
    )
    assert (
        suggest(
            request_data.model_copy(update={"llm_mode": "live"}), evaluation, client=client
        ).model_status
        == "unavailable"
    )
    assert evaluation.findings == (finding,)


def test_cache_publication_is_atomic(tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace

    import detect.client as module

    replace = os.replace
    published = []

    def inspect_replace(source, target):
        # A reader cannot see a partial final file, even while publication is paused.
        assert not target.exists()
        assert (
            CandidateBatch.model_validate_json(
                __import__("pathlib").Path(source).read_text()
            ).candidates
            == ()
        )
        published.append(target)
        replace(source, target)

    monkeypatch.setattr(module.os, "replace", inspect_replace)
    client = ModelClient(
        model="test",
        cache_dir=tmp_path,
        user_id="U-test",
        group="manager",
        acl_hash="test",
        transport=lambda **kw: SimpleNamespace(
            status="completed", output_parsed=CandidateBatch(candidates=())
        ),
    )
    assert (
        client.generate(
            purpose="test", payload={}, prompt="test", schema=CandidateBatch, mode="live"
        ).status
        == "live"
    )
    assert len(published) == 1 and len(list(tmp_path.iterdir())) == 1
