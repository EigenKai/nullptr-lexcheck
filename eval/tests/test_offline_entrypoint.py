import json
import socket

from eval.run import main


def test_offline_entrypoint_never_network(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setenv("LEXCHECK_LLM_MODE", "off")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    main()
    report = json.loads(capsys.readouterr().out)
    assert report["phase"] in ("bootstrap", "dev")
    if report["phase"] == "bootstrap":
        assert report["measured_cases"] == 0 and report["metrics"] is None
    else:
        assert report["n"] > 0 and all(s["model_calls"] == 0 for s in report["systems"])
