"""Single bounded transport boundary and permission-scoped response cache."""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import APITimeoutError
from pydantic import BaseModel, ValidationError


def cache_key(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def timeout_seconds():
    try:
        value = float(os.getenv("LEXCHECK_LLM_TIMEOUT_SECONDS", "60"))
    except ValueError:
        return 60.0
    return value if 0 < value <= 180 else 60.0


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
        authorize=None,
    ):
        self.authorize = authorize
        self.transport = transport
        self.model = model or os.getenv("OPENAI_MODEL")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.scope = {"user": user_id, "group": group, "acl": acl_hash, "pattern": pattern_version}

    def _authorized(self, payload):
        scoped = all(self.scope[k] for k in ("user", "group", "acl"))
        if os.getenv("LEXCHECK_LAYER3_ENABLED") == "1" and not scoped:
            return False
        snapshots = (payload.get("request", {}), payload.get("check", {}).get("snapshot", {}))
        records = tuple(r for snapshot in snapshots for r in snapshot.get("records", ()))
        group = self.scope["group"]
        if any(
            group not in r.get("access_groups", ())
            if group
            else not {"manager", "operations"}.issubset(r.get("access_groups", ()))
            for r in records
        ):
            return False
        try:
            return self.authorize is None or bool(self.authorize(payload))
        except Exception:  # noqa: BLE001 - authorization failure denies access
            return False

    def generate(self, *, purpose, payload, prompt, schema, mode):
        if mode == "off":
            return ModelOutput("off")
        if not self._authorized(payload):
            return ModelOutput("unavailable", error="access_denied")
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
        try:
            if self.transport is None:
                from openai import OpenAI

                with OpenAI(timeout=timeout_seconds(), max_retries=1) as client:
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
            raw = response.output_parsed
            parsed = schema.model_validate(raw.model_dump() if isinstance(raw, BaseModel) else raw)
        except ValidationError:
            return ModelOutput("unavailable", key=key, calls=1, error="schema_invalid")
        except APITimeoutError:
            return ModelOutput("unavailable", key=key, calls=1, error="timeout")
        except Exception:  # noqa: BLE001 - transport boundary must preserve deterministic results
            # Never expose transport exceptions containing private input or credentials.
            return ModelOutput("unavailable", key=key, calls=1, error="transport_failed")
        if path:
            temporary = None
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".response-")
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(parsed.model_dump_json())
                os.replace(temporary, path)
            except OSError:
                return ModelOutput("live", parsed, key, 1, "cache_write_failed")
            finally:
                if temporary is not None:
                    Path(temporary).unlink(missing_ok=True)
        return ModelOutput("live", parsed, key, 1)


def configured_client(**scope):
    return ModelClient(cache_dir=os.getenv("LEXCHECK_CACHE_DIR"), **scope)
