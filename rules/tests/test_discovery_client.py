"""SDK transport tests inject responses; never use credentials or network."""

import copy
import json
from types import SimpleNamespace

import pytest


class Client:
    def __init__(self, result, output=None, status="completed"):
        self.result, self.output, self.status = result, output or [], status
        self.calls = []
        self.responses = self

    def with_options(self, **options):
        return self

    def create(self, **options):
        self.calls.append(options)
        raw = {"id": "resp-test", "status": self.status, "output": self.output, "usage": {}}
        return SimpleNamespace(model_dump=lambda **_: raw, output_text=json.dumps(self.result))


def test_sdk_adapter_uses_structured_output_and_real_web_sources_only(tmp_path):
    from detect.client import DiscoveryTransport

    good = "https://vanban.chinhphu.vn/real"
    invented = "https://vanban.chinhphu.vn/invented"
    client = Client(
        {"sources": [{"url": good, "topic_ids": ["ads"]}, {"url": invented, "topic_ids": ["ads"]}]},
        [{"type": "web_search_call", "action": {"sources": [{"url": good}]}}],
    )
    adapter = DiscoveryTransport(client=client, model="test-model", cache_dir=tmp_path)
    schema = {
        "type": "object",
        "properties": {"sources": {"type": "array", "items": {"type": "string"}}},
    }
    result = adapter.complete(
        "search", {"company": {"company_id": "CO-ONE"}}, schema, timeout_s=5, web_search=True
    )
    assert [s["url"] for s in result["sources"]] == [good]
    assert client.calls[0]["store"] is False
    assert client.calls[0]["text"]["format"]["strict"] is True
    assert client.calls[0]["tools"][0]["type"] == "web_search"
    assert client.calls[0]["include"] == ["web_search_call.action.sources"]
    adapter.complete(
        "search", {"company": {"company_id": "CO-ONE"}}, schema, timeout_s=5, web_search=True
    )
    assert len(client.calls) == 1
    assert adapter.events[-1]["cached"] is True
    adapter.complete(
        "search", {"company": {"company_id": "CO-TWO"}}, schema, timeout_s=5, web_search=True
    )
    assert len(client.calls) == 2


def test_sdk_adapter_rejects_incomplete_and_search_without_actual_tool_call():
    from detect.client import DiscoveryTransport

    with pytest.raises(RuntimeError, match="incomplete"):
        DiscoveryTransport(client=Client({}, status="incomplete"), model="test-model").complete(
            "plan", {}, {}, timeout_s=5
        )
    with pytest.raises(RuntimeError, match="No actual"):
        DiscoveryTransport(client=Client({"sources": []}), model="test-model").complete(
            "search", {}, {}, timeout_s=5, web_search=True
        )


def test_strict_schema_is_derived_without_mutating_shared_schema():
    from detect.client import _strict

    schema = {
        "type": "object",
        "properties": {
            "optional": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None}
        },
    }
    before = copy.deepcopy(schema)
    strict = _strict(schema)
    assert schema == before
    assert strict["required"] == ["optional"]
    assert strict["additionalProperties"] is False
    assert "default" not in strict["properties"]["optional"]


def test_sdk_adapter_handles_optional_null_tool_content():
    from detect.client import DiscoveryTransport

    url = "https://vanban.chinhphu.vn/source"
    client = Client(
        {"sources": [{"url": url, "topic_ids": ["ads"]}]},
        [
            {"type": "reasoning", "content": None},
            {"type": "web_search_call", "content": None, "action": {"sources": [{"url": url}]}},
        ],
    )
    result = DiscoveryTransport(client=client, model="test-model").complete(
        "search", {}, {}, timeout_s=5, web_search=True
    )
    assert result["sources"][0]["url"] == url
