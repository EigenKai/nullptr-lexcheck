"""The discovery pipeline consumes transport results, never sample rule fallbacks."""

import copy
import json
from pathlib import Path

import pytest

from contracts.models import CheckRequest

ROOT = Path(__file__).resolve().parents[2]


def request():
    return CheckRequest.model_validate(
        json.loads((ROOT / "data/fixtures/demo.json").read_text("utf-8"))["request"]
    )


class Transport:
    def __init__(self, *, bad_quote=False, no_sources=False):
        self.calls = []
        self.bad_quote = bad_quote
        self.no_sources = no_sources

    def complete(self, stage, payload, schema, *, timeout_s, web_search=False):
        self.calls.append(stage)
        if stage == "plan":
            return {"topics": [{"id": "advertising", "question": "Quảng cáo cần khuyến cáo nào?"}]}
        if stage == "search":
            return {
                "sources": []
                if self.no_sources
                else [{"url": "https://vanban.chinhphu.vn/demo-law", "topic_ids": ["advertising"]}]
            }
        if stage == "extract":
            return {
                "candidates": [
                    {
                        "obligation_actor": "company",
                        "topic_id": "advertising",
                        "article": "Điều 1",
                        "page": 1,
                        "quote": "Câu không có trong nguồn"
                        if self.bad_quote
                        else "Quảng cáo phải ghi: CHỈ DÙNG NGOÀI.",
                        "valid_from": "2026-01-01",
                        "valid_to": None,
                        "title": "Khuyến cáo sinh từ nguồn test",
                        "concept": "Khuyến cáo quảng cáo",
                        "check_type": "warning",
                        "plan": {
                            "operation": "required_text",
                            "argument": "CHỈ DÙNG NGOÀI.",
                            "reference_kind": None,
                        },
                        "exceptions": ["Chỉ văn bản quảng cáo"],
                        "uncertainties": [],
                        "related_documents": [],
                    }
                ],
                "relations": [],
            }
        raise AssertionError(stage)


def fetcher(url):
    from rules.discovery import source_from_text

    return source_from_text(
        url,
        "Luật tổng hợp để test, không phải văn bản thật",
        "Điều 1. Quảng cáo phải ghi: CHỈ DÙNG NGOÀI.",
    )


def test_ingest_generates_source_grounded_rule_and_three_graph_layers(tmp_path):
    from rules.discovery import discover

    model = Transport()
    result = discover(request(), "Doanh nghiệp tổng hợp quảng cáo TPBVSK", model, fetcher=fetcher)
    assert len(result.rules) == 1
    assert result.rules[0].plan.argument == "CHỈ DÙNG NGOÀI."
    assert result.rules[0].rule.enabled is False
    assert result.stop_reason == "topic_coverage"
    assert result.missing_topics == ()
    assert {n["layer"] for n in result.graph.nodes.values()} == {1, 2, 3}
    assert {e["kind"] for e in result.graph.edges} >= {"DERIVED_FROM", "DETECTS", "HAS_VERSION"}
    assert result.graph.trace(result.rules[0].rule.id)
    path = tmp_path / "workspace.json"
    result.save(path)
    from rules.discovery import DiscoveryResult

    restored = DiscoveryResult.load(path, company_id="CO-DEMO")
    assert restored.rules[0].rule == result.rules[0].rule
    with pytest.raises(ValueError, match="company"):
        DiscoveryResult.load(path, company_id="CO-OTHER")


def test_audit_uses_generated_argument_without_new_search_or_model_call():
    from rules.discovery import audit, discover

    model = Transport()
    result = discover(request(), "Demo", model, fetcher=fetcher)
    calls = list(model.calls)
    first = audit(result, request())
    assert len(first["findings"]) == 2
    assert first["findings"][0]["rule_id"] == result.rules[0].rule.id
    assert first["mode"] == "candidate_preview"
    assert first["status"] == "not_enough_information"
    changed = request().model_dump(mode="json")
    for version in list(changed["versions"]):
        if version["id"] in changed["target_version_ids"]:
            replacement = copy.deepcopy(version)
            replacement["text"] += "\nCHỈ DÙNG NGOÀI."
            replacement["id"] = version["id"].replace("v1", "v2")
            replacement["version"] = 2
            replacement["supersedes"] = version["id"]
            changed["versions"].append(replacement)
            changed["target_version_ids"][changed["target_version_ids"].index(version["id"])] = (
                replacement["id"]
            )
    assert audit(result, CheckRequest.model_validate(changed))["findings"] == []
    assert model.calls == calls


def test_bogus_quote_is_rejected_and_never_replaced_by_samples():
    from rules.discovery import Budget, discover

    result = discover(
        request(), "Demo", Transport(bad_quote=True), fetcher=fetcher, budget=Budget(max_rounds=2)
    )
    assert result.rules == ()
    assert result.missing_topics == ("advertising",)
    assert any("quote_mismatch" in e for e in result.errors)
    assert not any(n["kind"] == "Rule" for n in result.graph.nodes.values())


def test_empty_search_stops_with_explicit_gaps():
    from rules.discovery import Budget, discover

    model = Transport(no_sources=True)
    result = discover(
        request(), "Demo", model, fetcher=fetcher, budget=Budget(max_rounds=6, stall_rounds=2)
    )
    assert model.calls.count("search") == 2
    assert result.stop_reason == "no_new_sources"
    assert result.missing_topics


def test_source_url_and_graph_immutability_are_enforced():
    from rules.discovery import discover, validate_url

    for url in [
        "http://vanban.chinhphu.vn/test",
        "https://chinhphu.vn.evil.test/a",
        "https://127.0.0.1/a",
        "https://vanban.chinhphu.vn:8443/a",
    ]:
        with pytest.raises(ValueError):
            validate_url(url)
    result = discover(request(), "Demo", Transport(), fetcher=fetcher)
    node = next(iter(result.graph.nodes))
    old = copy.deepcopy(result.graph.nodes[node])
    with pytest.raises(ValueError, match="immutable"):
        result.graph.add_node(node, old["layer"], old["kind"], {"different": True})
    assert result.graph.nodes[node] == old


def test_unresolved_law_references_are_followed_and_retained_as_gaps():
    from rules.discovery import Budget, audit, discover

    class WithReference(Transport):
        def complete(self, stage, payload, schema, **kwargs):
            result = super().complete(stage, payload, schema, **kwargs)
            if stage == "extract":
                result["candidates"][0]["related_documents"] = ["99/2026/NĐ-CP"]
            return result

    model = WithReference()
    result = discover(request(), "Demo", model, fetcher=fetcher, budget=Budget(stall_rounds=2))
    assert model.calls.count("search") > 1
    assert result.provenance["unresolved_documents"] == ["99/2026/NĐ-CP"]
    assert "unresolved_reference:99/2026/NĐ-CP" in audit(result, request())["coverage_gaps"]


def test_provider_failure_and_source_budget_do_not_invent_rules():
    from rules.discovery import Budget, discover

    class Broken:
        def complete(self, *args, **kwargs):
            raise RuntimeError("unavailable")

    assert discover(request(), "Demo", Broken(), fetcher=fetcher).rules == ()
    model = Transport(bad_quote=True)
    result = discover(request(), "Demo", model, fetcher=fetcher, budget=Budget(max_sources=1))
    assert result.rules == ()
    assert result.provenance["sources_attempted"] == 1


def test_clean_checks_create_dependencies_and_old_snapshots_are_preserved():
    from rules.discovery import audit, discover

    result = discover(request(), "Demo", Transport(), fetcher=fetcher)
    audit(result, request())
    original = copy.deepcopy(result.graph.nodes["RV-02-v1"])
    affected = result.graph.affected_records(result.rules[0].clause.id)
    assert {"RV-02-v1", "RV-03-v1"}.issubset(affected)
    assert result.graph.nodes["RV-02-v1"] == original
    assert any(n["kind"] == "AuditRun" for n in result.graph.nodes.values())


def test_tampered_quote_and_other_company_or_review_date_cannot_be_audited(tmp_path):
    from rules.discovery import DiscoveryResult, audit, discover

    result = discover(request(), "Demo", Transport(), fetcher=fetcher)
    path = tmp_path / "artifact.json"
    result.save(path)
    content = json.loads(path.read_text("utf-8"))
    content["rules"][0]["clause"]["text"] = "Tampered quote"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError, match="grounding"):
        DiscoveryResult.load(path, company_id="CO-DEMO")
    changed = request().model_dump(mode="json")
    changed["review_date"] = "2027-01-01"
    with pytest.raises(ValueError, match="Review date"):
        audit(result, CheckRequest.model_validate(changed))


@pytest.mark.parametrize(
    "operation,argument,reference_kind",
    [
        ("uses_subset", None, None),
        ("required_reference", None, "ad_confirmation"),
        ("forbidden_text", "CHỈ DÙNG NGOÀI.", None),
    ],
)
def test_generated_check_plans_are_executed_without_a_rule_id_registry(
    operation, argument, reference_kind
):
    from rules.discovery import audit, discover

    class Plan(Transport):
        def complete(self, stage, payload, schema, **kwargs):
            result = super().complete(stage, payload, schema, **kwargs)
            if stage == "extract":
                result["candidates"][0]["plan"] = {
                    "operation": operation,
                    "argument": argument,
                    "reference_kind": reference_kind,
                }
            return result

    result = discover(request(), "Demo", Plan(), fetcher=fetcher)
    report = audit(result, request())
    assert result.rules[0].rule.id in report["candidate_rules_inspected"]
    assert report["model_calls_during_audit"] == 0


def test_env_file_loader_only_reads_model_settings_without_overriding_process(
    tmp_path, monkeypatch
):
    from rules.discovery_cli import load_local_env

    monkeypatch.setenv("OPENAI_MODEL", "process-model")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    path = tmp_path / ".env"
    path.write_text(
        'OPENAI_MODEL=file-model\nOPENAI_API_KEY="test-only-not-a-real-key"\nSHOULD_NOT_BE_LOADED=yes\n',
        encoding="utf-8",
    )
    load_local_env(path)
    import os

    assert os.environ["OPENAI_MODEL"] == "process-model"
    assert os.environ["OPENAI_API_KEY"] == "test-only-not-a-real-key"
    assert "SHOULD_NOT_BE_LOADED" not in os.environ


@pytest.mark.parametrize(
    "change", ["wrong_article", "authority_obligation", "ungrounded_check_argument"]
)
def test_source_validation_rejects_wrong_article_actor_or_check_argument(change):
    from rules.discovery import Budget, discover

    class Invalid(Transport):
        def complete(self, stage, payload, schema, **kwargs):
            result = super().complete(stage, payload, schema, **kwargs)
            if stage == "extract":
                candidate = result["candidates"][0]
                if change == "wrong_article":
                    candidate["article"] = "Điều 99"
                elif change == "authority_obligation":
                    candidate["obligation_actor"] = "authority"
                else:
                    candidate["plan"]["argument"] = "Nội dung không có trong luật"
            return result

    result = discover(request(), "Demo", Invalid(), fetcher=fetcher, budget=Budget(max_rounds=1))
    assert not result.rules
    assert result.missing_topics


def test_graph_records_decision_and_keeps_patterns_as_candidates():
    from datetime import UTC, datetime

    from contracts.models import Decision, DecisionRequest, Pattern
    from rules.discovery import audit, discover

    class Forbidden(Transport):
        def complete(self, stage, payload, schema, **kwargs):
            result = super().complete(stage, payload, schema, **kwargs)
            if stage == "extract":
                result["candidates"][0]["plan"]["operation"] = "forbidden_text"
            return result

    raw = request().model_dump(mode="json")
    raw["versions"][1]["text"] += "\nCHỈ DÙNG NGOÀI."
    data = CheckRequest.model_validate(raw)
    result = discover(data, "Demo", Forbidden(), fetcher=fetcher)
    report = audit(result, data)
    finding = report["findings"][0]
    decision = Decision(
        id="DEC-TEST",
        request=DecisionRequest(
            check_id=report["id"],
            finding_id=finding["id"],
            action="confirm",
            actor="reviewer",
            note="Synthetic graph test only",
        ),
        task_status="open",
        created_at=datetime.now(UTC),
    )
    result.graph.record_decision(decision)
    pattern = Pattern(
        id="PAT-TEST",
        company_id="CO-DEMO",
        source_decision_id=decision.id,
        rule_id=finding["rule_id"],
        rule_version=finding["rule_version"],
        clause_version_id=finding["clause_version_id"],
        phrase="CHỈ DÙNG NGOÀI.",
        polarity="positive",
    )
    result.graph.record_pattern_candidate(pattern)
    assert result.graph.nodes[pattern.id]["payload"]["state"] == "candidate"
    with pytest.raises(ValueError, match="same-company"):
        result.graph.record_pattern_candidate(pattern.model_copy(update={"company_id": "CO-OTHER"}))


def test_source_fetch_strips_script_text_and_validates_redirects(monkeypatch):
    import hashlib

    from rules import legal_sources

    raw = (
        "<html><script>INJECTED INSTRUCTION</script><p>Điều 1. "
        + "Nguồn công khai. " * 20
        + "</p></html>"
    ).encode()

    class Response:
        def __init__(self):
            self.headers = {"Content-Type": "text/html; charset=utf-8"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, *args):
            return raw

        def geturl(self):
            return "https://vanban.chinhphu.vn/source"

    class Opener:
        def open(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(legal_sources, "build_opener", lambda *args: Opener())
    source = legal_sources.fetch_source("https://vanban.chinhphu.vn/source")
    assert source.sha256 == hashlib.sha256(raw).hexdigest()
    assert "INJECTED INSTRUCTION" not in source.pages[0]
    with pytest.raises(ValueError):
        legal_sources._Redirect().redirect_request(
            None, None, 302, "", {}, "https://evil.example/a"
        )
