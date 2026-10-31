from types import SimpleNamespace

from contracts.models import Evidence
from detect.client import ModelClient
from detect.rulegen import RuleCandidate, RuleCandidateBatch, propose_rules


def client_for(basis, *, quote=None, mode="completed", cache_dir=None):
    rule, clause, _ = basis
    evidence = Evidence(
        record_version_id=clause.id,
        kind="span",
        quote=quote or clause.text,
        start=0,
        end=len(clause.text),
    )
    batch = RuleCandidateBatch(candidates=(RuleCandidate(rule=rule, source_evidence=evidence),))
    return ModelClient(
        model="test",
        cache_dir=cache_dir,
        user_id="U-test",
        group="manager",
        acl_hash="test",
        transport=lambda **kw: SimpleNamespace(status=mode, output_parsed=batch),
    )


def test_off_mode_never_calls_network(basis, monkeypatch):
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "off")

    def forbidden(**kw):
        raise AssertionError("network forbidden")

    result = propose_rules(basis[1], client=ModelClient(model="test", transport=forbidden))
    assert result.mode == "unavailable" and not result.proposals


def test_rejects_quote_not_in_source(basis, monkeypatch):
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    result = propose_rules(basis[1], client=client_for(basis, quote="fabricated"))
    assert not result.proposals and result.rejected == 1


def test_proposals_are_disabled_and_unverified(basis, monkeypatch):
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    result = propose_rules(basis[1], client=client_for(basis))
    assert len(result.proposals) == 1
    assert result.proposals[0].id != basis[0].id
    assert not result.proposals[0].enabled
    assert result.proposals[0].verification_status == "to_be_verified"
    assert result.source_evidence[0].quote == basis[1].text


def test_cache_key_includes_clause_hash(basis, monkeypatch, tmp_path):
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    client = client_for(basis, cache_dir=tmp_path)
    first = propose_rules(basis[1], client=client)
    second = propose_rules(basis[1].model_copy(update={"text": "different clause"}), client=client)
    assert first.cache_key != second.cache_key


def test_rulegen_reference_system(monkeypatch):
    from eval.rulegen import evaluate_references, reference_inputs

    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    inputs = reference_inputs()
    assert len(inputs) == 3
    assert all(not any(k.startswith("expected") for k in item) for item in inputs)
    import json

    from contracts.models import Rule

    def transport(**kwargs):
        source = json.loads(kwargs["input"])["clause"]
        rule = Rule(
            id="R-test",
            version=1,
            clause_version_id=source["id"],
            title="Test only",
            check_type="warning",
        )
        evidence = Evidence(
            record_version_id=source["id"],
            kind="span",
            quote=source["text"],
            start=0,
            end=len(source["text"]),
        )
        good = RuleCandidate(rule=rule, source_evidence=evidence)
        bad = good.model_copy(
            update={"source_evidence": evidence.model_copy(update={"quote": "fabricated"})}
        )
        return SimpleNamespace(
            status="completed", output_parsed=RuleCandidateBatch(candidates=(good, bad))
        )

    client = ModelClient(model="test", transport=transport)
    result = evaluate_references(client=client)
    assert result == {
        "n": 3,
        "structurally_valid": 6,
        "grounded": 3,
        "rejected": 3,
        "unavailable": 0,
        "legal_accuracy_measured": False,
    }


def test_no_key_returns_no_proposals(basis, monkeypatch):
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "live")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert propose_rules(basis[1], client=ModelClient(model="test")).mode == "unavailable"
