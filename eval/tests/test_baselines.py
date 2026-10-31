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
