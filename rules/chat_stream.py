"""Actual Responses SSE transport around the unchanged canonical ModelClient."""

import copy
import json
import os
import tempfile

import httpx
from pydantic_core import from_json

from detect.client import ModelOutput, timeout_seconds


class StreamCancelled(RuntimeError):
    pass


def check_cancelled(cancelled):
    if cancelled is not None and cancelled.is_set():
        raise StreamCancelled("Chat request cancelled.")


def json_objects(text):
    """Ignore provider prose/format labels; never forward them as answer text."""
    for position, character in enumerate(text):
        if character == "{":
            yield text[position:]


def parse_structured(schema, text):
    try:
        return schema.model_validate_json(text)
    except ValueError:
        decoder = json.JSONDecoder()
        for candidate in json_objects(text):
            try:
                value, _ = decoder.raw_decode(candidate)
                return schema.model_validate(value)
            except ValueError:
                continue
        raise


class AnswerDeltas:
    def __init__(self, emit, *, root_answer=False):
        self.emit, self.root_answer = emit, root_answer
        self.buffer, self.sent = "", ""

    def feed(self, delta):
        self.buffer += delta
        for candidate in json_objects(self.buffer):
            try:
                partial = from_json(candidate, allow_partial="trailing-strings")
            except ValueError:
                continue
            if not isinstance(partial, dict):
                continue
            if self.root_answer:
                answer = partial.get("answer")
            elif partial.get("tool") == "final_answer" and isinstance(partial.get("final"), dict):
                answer = partial["final"].get("answer")
            else:
                continue
            if (
                isinstance(answer, str)
                and answer.startswith(self.sent)
                and len(answer) > len(self.sent)
            ):
                self.emit("answer_delta", {"text": answer[len(self.sent) :]})
                self.sent = answer
                break


def strict_schema(schema):
    result = copy.deepcopy(schema)

    def visit(value):
        if isinstance(value, dict):
            value.pop("default", None)
            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(result)
    return result


class StreamingModelClient:
    def __init__(self, base, emit, cancelled, *, http_client=None):
        self.base, self.model = base, base.model
        self.emit, self.cancelled = emit, cancelled
        self.http_client, self.active_response = http_client, None

    def cancel(self):
        self.cancelled.set()
        if self.active_response is not None:
            try:
                self.active_response.close()
            except httpx.HTTPError:
                pass

    def generate(self, **kwargs):
        check_cancelled(self.cancelled)
        kwargs = {
            **kwargs,
            "prompt": kwargs["prompt"]
            + " Return only the requested JSON object. Do not add Thought/Action labels, Markdown fences or prose outside the JSON object.",
        }
        cached = self.base.generate(
            **{**kwargs, "mode": "off" if kwargs.get("mode") == "off" else "cache"}
        )
        if cached.status in ("cached", "live") and cached.parsed is not None:
            self._emit_complete(cached.parsed)
            return cached
        if cached.error != "cache_miss" or kwargs.get("mode") != "live":
            return cached
        if getattr(self.base, "transport", None) is not None:
            result = self.base.generate(**kwargs)
            if result.parsed is not None:
                self._emit_complete(result.parsed)
            return result
        if not os.getenv("OPENAI_API_KEY"):
            return ModelOutput("unavailable", key=cached.key, error="credentials_missing")
        schema = kwargs["schema"]
        deltas = AnswerDeltas(self.emit, root_answer="answer" in schema.model_fields)
        options = {
            "model": self.model,
            "instructions": kwargs["prompt"],
            "input": json.dumps(kwargs["payload"], ensure_ascii=False),
            "store": False,
            "stream": True,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__,
                    "strict": True,
                    "schema": strict_schema(schema.model_json_schema()),
                }
            },
        }
        client = self.http_client or httpx.Client(timeout=timeout_seconds())
        completed = False
        completed_text = ""
        self.emit(
            "progress", {"tool": "model", "status": "generating", "message": "Đang xử lý yêu cầu…"}
        )
        try:
            endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            with client.stream(
                "POST",
                endpoint + "/responses",
                headers={
                    "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                    "Accept": "text/event-stream",
                },
                json=options,
            ) as response:
                self.active_response = response
                response.raise_for_status()
                lines = []
                for line in response.iter_lines():
                    check_cancelled(self.cancelled)
                    if line:
                        if line.startswith("data:"):
                            lines.append(line[5:].lstrip())
                        continue
                    if not lines:
                        continue
                    raw = "\n".join(lines)
                    lines = []
                    if raw == "[DONE]":
                        continue
                    event = json.loads(raw)
                    kind = event.get("type")
                    if kind == "response.output_text.delta":
                        deltas.feed(event.get("delta", ""))
                    elif kind == "response.completed":
                        completed = (
                            event.get("response", {}).get("status", "completed") == "completed"
                        )
                        completed_text = "".join(
                            part.get("text", "")
                            for output in event.get("response", {}).get("output", [])
                            for part in output.get("content", [])
                            if part.get("type") == "output_text"
                        )
                    elif kind in ("error", "response.failed", "response.incomplete"):
                        raise RuntimeError("Provider stream did not complete.")
            check_cancelled(self.cancelled)
            if not completed:
                raise RuntimeError("Provider stream ended before completion.")
            parsed = parse_structured(schema, completed_text or deltas.buffer)
            if not self.base._authorized(kwargs["payload"]):
                return ModelOutput("unavailable", key=cached.key, calls=1, error="access_denied")
            self._cache(cached.key, parsed)
            return ModelOutput("live", parsed, cached.key, 1)
        except Exception:
            check_cancelled(self.cancelled)
            raise
        finally:
            self.active_response = None
            if self.http_client is None:
                client.close()

    def _emit_complete(self, parsed):
        data = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        if isinstance(data, dict):
            final = data.get("final") if data.get("tool") == "final_answer" else data
            if isinstance(final, dict) and isinstance(final.get("answer"), str):
                self.emit("answer_delta", {"text": final["answer"]})

    def _cache(self, key, parsed):
        if not self.base.cache_dir or not all(
            self.base.scope.get(name) for name in ("user", "group", "acl")
        ):
            return
        check_cancelled(self.cancelled)
        folder = self.base.cache_dir
        folder.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=folder, prefix=".stream-")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(parsed.model_dump_json())
            check_cancelled(self.cancelled)
            os.replace(temporary, folder / (key + ".json"))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
