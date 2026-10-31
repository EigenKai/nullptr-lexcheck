from detect.service import suggest
from detect.validator import validate_findings
from intake.fixtures import load_demo
from rules.engine import evaluate


def test_bootstrap_demo_without_key_or_network(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bundle = load_demo()
    evaluation = evaluate(bundle.request)
    assert evaluation.mode in ("fixture", "live")
    assert suggest(bundle.request, evaluation).model_status == "off"
    assert validate_findings((), bundle.request, bundle.rules, bundle.clauses).findings == ()
    result = client.post("/api/check", json=bundle.request.model_dump(mode="json"))
    assert result.status_code == 200
    if result.json()["mode"] == "fixture":
        assert result.json()["rules_checked"] == []
        assert result.json()["status"] == "not_enough_information"
    assert all(not rule.enabled or rule.verification_status == "verified" for rule in bundle.rules)
