"""Single-worker, atomic demo snapshots. Sessions never enter this file."""

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from contracts.models import (
    ChangeEvent,
    CheckResult,
    Decision,
    LegalChangeState,
    Pattern,
    RecheckItem,
    Record,
    RecordVersion,
    Rule,
)
from intake.fixtures import load_demo


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    action: str
    entity_id: str
    user_id: str
    note: str
    created_at: datetime


class State(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: dict[str, Record] = Field(default_factory=dict)
    versions: dict[str, RecordVersion] = Field(default_factory=dict)
    checks: dict[str, CheckResult] = Field(default_factory=dict)
    decisions: dict[str, Decision] = Field(default_factory=dict)
    events: dict[str, ChangeEvent] = Field(default_factory=dict)
    queue: dict[str, RecheckItem] = Field(default_factory=dict)
    legal_changes: dict[str, LegalChangeState] = Field(default_factory=dict)
    patterns: dict[str, Pattern] = Field(default_factory=dict)
    activations: dict[str, tuple[Rule, ...]] = Field(default_factory=dict)
    audit: tuple[AuditEntry, ...] = ()


def put_immutable(mapping, item):
    if item.id in mapping and mapping[item.id] != item:
        raise HTTPException(409, "conflict")
    mapping[item.id] = item


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.lock = RLock()
        if self.path.exists():
            # Invalid persisted data fails startup; never silently discard history.
            self.data = State.model_validate_json(self.path.read_text(encoding="utf-8"))
        else:
            bundle = load_demo()
            self.data = State(
                records={r.id: r for r in bundle.request.records},
                versions={v.id: v for v in bundle.request.versions},
            )
        # Server-owned demo ACL; a client snapshot cannot grant access to private records.
        access_path = Path(__file__).resolve().parents[1] / "data/fixtures/access.json"
        access = json.loads(access_path.read_text(encoding="utf-8"))
        for name in ("shared_request", "manager_request"):
            for item in access[name]["records"]:
                record = Record.model_validate(item)
                if record.id in self.data.records:
                    current = self.data.records[record.id]
                    self.data.records[record.id] = current.model_copy(
                        update={"access_groups": record.access_groups}
                    )

    def __getattr__(self, key):
        if key in State.model_fields:
            return getattr(self.data, key)
        raise AttributeError(key)

    @contextmanager
    def transaction(self):
        with self.lock:
            before = self.data
            self.data = before.model_copy(deep=True)
            try:
                yield self
                self._persist()
            except BaseException:
                self.data = before
                raise

    def _persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(prefix=".state-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(self.data.model_dump(mode="json"), stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def save_check(self, check):
        with self.transaction():
            self.register_check(check)

    def register_check(self, check):
        """Register inside an existing transaction, retaining server-owned ACL."""
        for record in check.snapshot.records:
            original = self.records.get(record.id)
            if original and original.model_dump(exclude={"access_groups"}) == record.model_dump(
                exclude={"access_groups"}
            ):
                continue
            put_immutable(self.records, record)
        for version in check.snapshot.versions:
            put_immutable(self.versions, version)
        put_immutable(self.checks, check)
