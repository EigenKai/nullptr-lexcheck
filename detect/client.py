"""Single bounded transport boundary and permission-scoped response cache."""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError


def cache_key(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class ModelOutput:
    status: str
    parsed: Any = None
    key: str | None = None
    calls: int = 0
    error: str | None = None


class ModelClient:
    def __init__(
        self,
        *,
        transport=None,
        model=None,
        cache_dir=None,
        user_id=None,
        group=None,
        acl_hash=None,
        pattern_version="none",
    ):
        self.transport = transport
        self.model = model or os.getenv("OPENAI_MODEL")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.scope = {"user": user_id, "group": group, "acl": acl_hash, "pattern": pattern_version}

    def generate(self, *, purpose, payload, prompt, schema, mode):
        if mode == "off":
            return ModelOutput("off")
        if not self.model:
            return ModelOutput("unavailable", error="model_missing")
        key = cache_key(
            {
                "purpose": purpose,
                "model": self.model,
                "schema": schema.model_json_schema(),
                "prompt": prompt,
                "payload": payload,
                "scope": self.scope,
            }
        )
        scoped = all(self.scope[k] for k in ("user", "group", "acl"))
        path = self.cache_dir / (key + ".json") if self.cache_dir and scoped else None
        if path and path.is_file():
            try:
                return ModelOutput("cached", schema.model_validate_json(path.read_text()), key)
            except (OSError, ValueError, ValidationError):
                return ModelOutput("unavailable", key=key, error="cache_invalid")
        if mode != "live":
            return ModelOutput("unavailable", key=key, error="cache_miss")
        return self._live(payload, prompt, schema, key, path)

    def _live(self, payload, prompt, schema, key, path):
        if self.transport is None and not os.getenv("OPENAI_API_KEY"):
            return ModelOutput("unavailable", key=key, error="credentials_missing")
        transport_errors = (TimeoutError, OSError, ValueError)
        try:
            if self.transport is None:
                from openai import OpenAI, OpenAIError

                transport_errors = (*transport_errors, OpenAIError)
                with OpenAI(timeout=15.0, max_retries=1) as client:
                    response = client.responses.parse(
                        model=self.model,
                        instructions=prompt,
                        input=json.dumps(payload, ensure_ascii=False),
                        text_format=schema,
                        store=False,
                    )
            else:
                response = self.transport(
                    model=self.model,
                    instructions=prompt,
                    input=json.dumps(payload, ensure_ascii=False),
                    text_format=schema,
                    store=False,
                )
            if response.status != "completed" or response.output_parsed is None:
                return ModelOutput("unavailable", key=key, calls=1, error="no_complete_output")
            parsed = schema.model_validate(response.output_parsed)
        except transport_errors:
            # Never expose transport exceptions containing private input or credentials.
            return ModelOutput("unavailable", key=key, calls=1, error="transport_failed")
        if path:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("x", encoding="utf-8") as handle:
                    handle.write(parsed.model_dump_json())
                path.chmod(0o600)
            except FileExistsError:
                pass
            except OSError:
                return ModelOutput("live", parsed, key, 1, "cache_write_failed")
        return ModelOutput("live", parsed, key, 1)


def configured_client(**scope):
    return ModelClient(cache_dir=os.getenv("LEXCHECK_CACHE_DIR"), **scope)
