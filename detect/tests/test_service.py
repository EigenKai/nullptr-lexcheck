import builtins
import socket

from contracts.models import RuleEvaluation
from detect.service import suggest


def test_off_mode_never_creates_client(request_data, monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        assert name != "openai"
        return original(name, *args, **kwargs)

    def denied(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluation = RuleEvaluation(mode="live", applicability="applies", reason="Test only")
    assert suggest(request_data, evaluation).model_status == "off"
    assert (
        suggest(request_data.model_copy(update={"llm_mode": "live"}), evaluation).model_status
        == "off"
    )
