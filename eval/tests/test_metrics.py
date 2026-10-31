from eval.metrics import pair_metrics, per_rule, stability


def test_metrics_include_false_clean_and_per_rule():
    gold = {("RV-01", "R-01")}
    assert pair_metrics(set(), gold)["false_clean"]
    assert per_rule([(set(), gold)])["R-01"]["false_negative"] == 1


def test_stability_unavailable_not_negative():
    unavailable = [
        {"case": "test", "predictions": {"keyword": None, "plain_chat": None, "lexcheck": None}}
    ]
    assert stability([unavailable] * 3)["lexcheck"]["agreement"] is None
    measured = [
        {
            "case": "test",
            "plain_status": "live",
            "lexcheck_status": "live",
            "predictions": {"keyword": [], "plain_chat": [], "lexcheck": []},
        }
    ]
    assert stability([measured] * 3)["lexcheck"]["agreement"] == 1
    changed = [
        {
            "case": "test",
            "predictions": {"keyword": [], "plain_chat": [], "lexcheck": [["RV-01", "R-01"]]},
            "plain_status": "live",
            "lexcheck_status": "live",
        }
    ]
    assert stability([measured, measured, changed])["lexcheck"]["agreement"] == 0


def test_stability_cli_offline(monkeypatch, capsys):
    import json
    import socket

    from eval.stability import main

    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "off")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    main()
    result = json.loads(capsys.readouterr().out)
    assert result["n"] == 15 and result["repeats"] == 3 and result["model_calls"] == 0


def test_stability_excludes_cached_model_responses():
    trace = [
        {
            "case": "test",
            "predictions": {"keyword": [], "plain_chat": [], "lexcheck": []},
            "plain_status": "cached",
            "lexcheck_status": "cached",
        }
    ]
    result = stability([trace] * 3)
    assert result["plain_chat"]["agreement"] is None
    assert result["plain_chat"]["cached_cases"] == 1
