"""Private, isolated workspace artifacts, independent of the shared demo API."""

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from rules.workbook import summarize_workbook


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class WorkspaceStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def folder(self, workspace_id):
        if not re.fullmatch(r"WS-[a-f0-9]{24}", workspace_id):
            raise ValueError("Invalid workspace ID.")
        return self.root / workspace_id

    def create(self, name, raw, *, review_date=None, description=""):
        if not 1 <= len(name.strip()) <= 150 or len(description) > 2000:
            raise ValueError("Invalid workspace name or description.")
        manifest = summarize_workbook(raw)
        workspace_id = "WS-" + uuid.uuid4().hex[:24]
        folder = self.folder(workspace_id)
        folder.mkdir()
        (folder / "source.xlsx").write_bytes(raw)
        workspace = {
            "id": workspace_id,
            "name": name.strip(),
            "domain": "rental_housing",
            "description": description,
            "review_date": str(review_date or date.today()),
            "created_at": datetime.now(UTC).isoformat(),
            "manifest": manifest,
            "state": "ready",
            "progress": [],
            "runs": [],
            "latest_run": None,
            "private_local_example": True,
        }
        write_json(folder / "workspace.json", workspace)
        return workspace

    def get(self, workspace_id):
        return json.loads(
            (self.folder(workspace_id) / "workspace.json").read_text(encoding="utf-8")
        )

    def list(self):
        return sorted(
            (
                self.get(path.name)
                for path in self.root.glob("WS-*")
                if (path / "workspace.json").is_file()
            ),
            key=lambda item: item["created_at"],
        )

    def update(self, workspace_id, **fields):
        if set(fields) - {"name", "state", "progress", "runs", "latest_run"}:
            raise ValueError("Immutable workspace field.")
        if "name" in fields:
            if not isinstance(fields["name"], str) or not 1 <= len(fields["name"].strip()) <= 150:
                raise ValueError("Invalid workspace name.")
            fields["name"] = fields["name"].strip()
        with self._lock:
            workspace = self.get(workspace_id)
            workspace.update(fields)
            write_json(self.folder(workspace_id) / "workspace.json", workspace)
            return workspace

    def progress(self, workspace_id, stage, message):
        with self._lock:
            workspace = self.get(workspace_id)
            events = workspace["progress"] + [
                {"stage": stage, "message": message, "at": datetime.now(UTC).isoformat()}
            ]
            self.update(workspace_id, progress=events[-100:])

    def finish(self, workspace_id, result):
        if result["graph"]["company_id"] != workspace_id:
            raise ValueError("Wrong workspace scope.")
        with self._lock:
            workspace = self.get(workspace_id)
            run_id = "RUN-" + uuid.uuid4().hex[:24]
            write_json(self.folder(workspace_id) / "runs" / (run_id + ".json"), result)
            self.update(
                workspace_id,
                latest_run=run_id,
                runs=workspace["runs"] + [run_id],
                state="review_needed",
            )
            return run_id

    def result(self, workspace_id):
        workspace = self.get(workspace_id)
        if not workspace["latest_run"]:
            return None
        return json.loads(
            (self.folder(workspace_id) / "runs" / (workspace["latest_run"] + ".json")).read_text(
                encoding="utf-8"
            )
        )
