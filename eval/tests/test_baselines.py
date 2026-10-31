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
    rule = Rule.model_validate(basis["rule"])
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
    assert report.systems[2].evaluated_cases == 1
    assert report.systems[2].true_positive == 1
    assert trace[0]["rejected"] == {"quote_mismatch": 1}
    assert received[0] == received[1]
    assert "gold" not in str(received)
