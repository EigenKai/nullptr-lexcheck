from eval.baselines import model_input, score
from intake.fixtures import load_demo


def test_same_inputs_for_both_baselines():
    bundle = load_demo()
    payload = model_input(bundle.request, bundle.rules, bundle.clauses)
    assert payload == model_input(bundle.request, bundle.rules, bundle.clauses)
    assert "gold" not in str(payload)
    assert payload["clauses"] == [c.model_dump(mode="json") for c in bundle.clauses]


def test_zero_denominator_is_null():
    result = score("keyword", [], 0, 0)
    assert result.precision is None and result.recall is None


def test_keyword_changes_with_input():
    from eval.baselines import keyword

    request = load_demo().request
    original = keyword(request, {"R-01", "R-02", "R-03", "R-04", "R-05"})
    versions = tuple(
        v.model_copy(update={"text": "Chữa khỏi bệnh", "uses": ("different use",)})
        if v.id in request.target_version_ids
        else v
        for v in request.versions
    )
    changed = keyword(
        request.model_copy(update={"versions": versions}), {"R-01", "R-02", "R-03", "R-04", "R-05"}
    )
    assert changed != original
    assert ("RV-02-v1", "R-01") in changed
    assert ("RV-02-v1", "R-05") in changed


def test_failed_predictions_not_negative():
    result = score("plain_chat", [], 2, 2)
    assert result.evaluated_cases == 0 and result.false_negative == 0
    assert result.failed_calls == 2
    positive = score("keyword", [({("RV-01", "R-01")}, {("RV-01", "R-01")})], 0, 0)
    assert positive.precision == 1 and positive.recall == 1


def test_rejected_proposals_remain_in_denominator(monkeypatch):
    import json
    from types import SimpleNamespace

    from contracts.models import ClauseVersion, Evidence, Rule, RuleEvaluation
    from detect.candidates import Candidate, CandidateBatch
    from detect.client import ModelClient
    from eval.run import ROOT, evaluate_cases

    basis = json.loads((ROOT / "detect/tests/fixtures/basis.json").read_text())
    rule = Rule.model_validate({**basis["rule"], "check_type": "endorsement"})
    clause = ClauseVersion.model_validate(basis["clause"])
    request = load_demo().request
    version = next(v for v in request.versions if v.id in request.target_version_ids)
    candidate = Candidate(
        rule_id=rule.id,
        record_version_id=version.id,
        clause_quote=clause.text,
        evidence=(
            Evidence(
                record_version_id=version.id, kind="span", quote=version.text[:5], start=0, end=5
            ),
        ),
    )
    returned = CandidateBatch(
        candidates=(candidate, candidate.model_copy(update={"clause_quote": "fabricated"}))
    )
    received = []

    def engine(request):
        return RuleEvaluation(
            mode="live",
            applicability="applies",
            reason="Test only",
            rules_checked=(rule.id,),
            rule_snapshots=(rule,),
            clause_snapshots=(clause,),
        )

    def transport(**kw):
        received.append(json.loads(kw["input"]))
        return SimpleNamespace(status="completed", output_parsed=returned)

    monkeypatch.setattr("eval.run.evaluate", engine)
    client = ModelClient(model="test", transport=transport)
    report, trace = evaluate_cases(
        (("test", request, {"gold": [[version.id, rule.id]]}),), mode="live", client=client
    )
    assert report.rule_ids == (rule.id,)
    assert report.systems[-1].evaluated_cases == 1
    assert report.systems[-1].true_positive == 1
    assert trace[0]["rejected"] == {"quote_mismatch": 1}
    assert received[0] == received[1]
    assert "gold" not in str(received)


def test_plain_input_excludes_patterns_and_examples():
    bundle = load_demo()
    rules = tuple(
        rule.model_copy(
            update={"patterns": ("private pattern",), "positive_examples": ("example answer",)}
        )
        for rule in bundle.rules
    )
    payload = model_input(bundle.request, rules, bundle.clauses)
    assert all(
        "patterns" not in rule
        and "positive_examples" not in rule
        and "negative_examples" not in rule
        for rule in payload["rules"]
    )


def _baseline_run(transport):
    from detect.client import ModelClient
    from eval.run import ROOT, evaluate_cases, load_cases

    return evaluate_cases(
        load_cases(ROOT / "data/dev")[:1],
        mode="live",
        client=ModelClient(model="test", transport=transport),
    )


def test_bplus_same_prompt_and_input_as_plain_plus_web_search():
    from types import SimpleNamespace

    from detect.candidates import CandidateBatch

    received = []

    def transport(**kwargs):
        received.append(kwargs)
        return SimpleNamespace(status="completed", output_parsed=CandidateBatch(candidates=()))

    _baseline_run(transport)
    plain, web = received[:2]
    assert web["instructions"] == plain["instructions"]
    assert web["input"] == plain["input"]
    assert "tools" not in plain
    assert web["tools"] == [{"type": "web_search"}]


def test_retrieval_top3_deterministic():
    from eval.retrieval import retrieve

    first = retrieve("khuyến cáo thuốc chữa bệnh màu tương phản")
    assert len(first) == 3 and first == retrieve("khuyến cáo thuốc chữa bệnh màu tương phản")
    assert first != retrieve("Giấy xác nhận đăng ký nội dung quảng cáo")
    assert [p["id"] for p in retrieve("")] == sorted(p["id"] for p in retrieve(""))


def test_retrieval_payload_replaces_clauses_only():
    from eval.retrieval import retrieval_payload, retrieve

    bundle = load_demo()
    payload = model_input(bundle.request, bundle.rules, bundle.clauses)
    result = retrieval_payload(payload)
    assert {k: v for k, v in result.items() if k != "clauses"} == {
        k: v for k, v in payload.items() if k != "clauses"
    }
    query = "\n".join(
        v.text for v in bundle.request.versions if v.id in bundle.request.target_version_ids
    )
    assert result["clauses"] == list(retrieve(query))
    assert len(result["clauses"]) == 3 and result["clauses"] != payload["clauses"]
    assert payload["clauses"] == [c.model_dump(mode="json") for c in bundle.clauses]


def test_new_baseline_failure_is_unavailable_not_negative():
    def failed(**kwargs):
        raise RuntimeError("unsupported tools or private failure")

    report, trace = _baseline_run(failed)
    for name in ("plain_chat_web", "retrieval"):
        score = next(s for s in report.systems if s.system == name)
        assert score.evaluated_cases == 0 and score.false_negative == 0
        assert score.model_calls == 1 and score.failed_calls == 1
        assert trace[0]["predictions"][name] is None
        assert trace[-1]["errors"][name] == {"transport_failed": 1}
