"""Streaming sends actual structured answer deltas and saves completed turns only."""

import json
import threading
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from detect.client import ModelClient
from rules.chat_stream import AnswerDeltas, StreamCancelled, StreamingModelClient
from rules.workspace_chat import AnswerDraft


def test_partial_structured_answer_preserves_unicode_and_escapes():
    events = []
    parser = AnswerDeltas(lambda kind, data: events.append((kind, data)))
    raw = json.dumps(
        {"tool": "final_answer", "final": {"answer": '**Chào**\n"bạn" 🌱'}}, ensure_ascii=False
    )
    for character in raw:
        parser.feed(character)
    assert len(events) > 2
    assert "".join(data["text"] for _, data in events) == '**Chào**\n"bạn" 🌱'
    other = AnswerDeltas(lambda *_: pytest.fail("Tool planning leaked as answer text"))
    other.feed('{"tool":"web_search","query":"hello","final":null}')


def test_provider_labelled_json_stream_does_not_leak_planning():
    from rules.chat_stream import parse_structured

    draft = AnswerDraft(
        answer="Visible answer", status="answered", answer_type="conversation", citations=[]
    )
    raw = "Thought: private planning text.\nAction:\n```json\n" + draft.model_dump_json() + "\n```"
    assert parse_structured(AnswerDraft, raw) == draft
    events = []
    parser = AnswerDeltas(lambda kind, data: events.append(data["text"]), root_answer=True)
    for piece in raw:
        parser.feed(piece)
    assert "".join(events) == "Visible answer"


def test_actual_sse_transport_emits_before_completion_and_honors_cancel(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://provider.example/v1")
    cancelled, events = threading.Event(), []
    raw = AnswerDraft(
        answer="Hello world", status="answered", answer_type="conversation", citations=[]
    ).model_dump_json()

    class Wire(httpx.SyncByteStream):
        def __iter__(self):
            for piece in (raw[:25], raw[25:]):
                yield (
                    "data: "
                    + json.dumps({"type": "response.output_text.delta", "delta": piece})
                    + "\n\n"
                ).encode()
            assert any(kind == "answer_delta" for kind, _ in events)
            yield b'data: {"type":"response.completed","response":{"status":"completed"}}\n\n'

    def handler(request):
        assert str(request.url) == "https://provider.example/v1/responses"
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, stream=Wire())

    base = ModelClient(model="synthetic", cache_dir=tmp_path, user_id="u", group="g", acl_hash="a")
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = StreamingModelClient(
            base, lambda kind, data: events.append((kind, data)), cancelled, http_client=http
        )
        args = {
            "purpose": "stream",
            "payload": {},
            "prompt": "synthetic",
            "schema": AnswerDraft,
            "mode": "live",
        }
        output = client.generate(**args)
        assert output.calls == 1 and output.parsed.answer == "Hello world"
        assert (
            "".join(data["text"] for kind, data in events if kind == "answer_delta")
            == "Hello world"
        )
        assert client.generate(**args).status == "cached"
        events.clear()

        def cancel_on_delta(kind, data):
            events.append((kind, data))
            if kind == "answer_delta":
                cancelled.set()

        client.emit = cancel_on_delta
        with pytest.raises(StreamCancelled):
            client.generate(**{**args, "purpose": "cancel-in-flight"})
        assert len(list(tmp_path.glob("*.json"))) == 1


def test_stream_route_saves_exactly_one_completed_turn(tmp_path, monkeypatch):
    from rules.workspace_app import create_app

    monkeypatch.setenv("LEXCHECK_WORKSPACE_CHAT_ENABLED", "1")
    monkeypatch.delenv("LEXCHECK_WORKSPACE_TOOL_HARNESS_ENABLED", raising=False)

    def transport(**kwargs):
        schema = kwargs["text_format"]
        value = (
            {"queries": ["hello"], "read_documents": []}
            if "queries" in schema.model_fields
            else {
                "answer": "Hello **there**",
                "status": "answered",
                "answer_type": "conversation",
                "citations": [],
            }
        )
        return SimpleNamespace(status="completed", output_parsed=value)

    app = create_app(
        tmp_path,
        enabled=True,
        chat_client_factory=lambda _: ModelClient(model="synthetic", transport=transport),
    )
    with TestClient(app) as client:
        headers = {"X-Workspace-Token": app.state.token}
        from rules.workspaces import WorkspaceStore

        workspace = WorkspaceStore(tmp_path).create_blank("Synthetic")
        conversation = client.post(
            f"/api/workspaces/{workspace['id']}/conversations", headers=headers, json={}
        ).json()
        url = f"/api/workspaces/{workspace['id']}/conversations/{conversation['id']}"
        response = client.post(
            url + "/messages/stream", headers=headers, json={"question": "Hello"}
        )
        assert response.status_code == 200
        assert "event: answer_delta" in response.text and "event: done" in response.text
        assert "event: error" not in response.text
        assert len(client.get(url, headers=headers).json()["turns"]) == 1
