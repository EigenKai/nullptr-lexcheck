"""Private, isolated workspace artifacts, independent of the shared demo API."""

import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from rules.documents import extract_document
from rules.knowledge_graph import KnowledgeGraph, stable_id
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
        if any(part.lower() in ("test_final", "nullptr-test-final") for part in self.root.parts):
            raise ValueError("Held-out evaluation paths are not workspace stores.")
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

    def create_blank(self, name, *, description="", reference_key=None, synthetic=False):
        if (
            not isinstance(name, str)
            or not 1 <= len(name.strip()) <= 150
            or len(description) > 2000
        ):
            raise ValueError("Invalid workspace name or description.")
        workspace_id = "WS-" + uuid.uuid4().hex[:24]
        self.folder(workspace_id).mkdir()
        workspace = {
            "id": workspace_id,
            "name": name.strip(),
            "description": description,
            "domain": "unclassified",
            "created_at": datetime.now(UTC).isoformat(),
            "review_date": str(date.today()),
            "state": "ready",
            "progress": [],
            "runs": [],
            "latest_run": None,
            "documents": [],
            "reference_key": reference_key,
            "synthetic": synthetic,
            "private_local_example": True,
            "profile": None,
        }
        write_json(self.folder(workspace_id) / "workspace.json", workspace)
        return workspace

    def migrate_documents(self, workspace_id):
        with self._lock:
            workspace = self.get(workspace_id)
            if "documents" in workspace:
                return workspace
            workspace["documents"] = []
            workspace["legacy_research_context"] = (
                "Developer-configured housing context; rerun with reviewed company inputs before reuse."
            )
            write_json(self.folder(workspace_id) / "workspace.json", workspace)
            original = self.folder(workspace_id) / "source.xlsx"
            if original.is_file():
                self.add_document(workspace_id, "business", "source.xlsx", original.read_bytes())
            result = self.result(workspace_id)
            if result:
                for node in result["graph"]["nodes"].values():
                    if node["kind"] != "LegalDoc":
                        continue
                    source = node["payload"]
                    for suffix in (".pdf", ".html"):
                        path = self.folder(workspace_id) / "sources" / (source["sha256"] + suffix)
                        if path.is_file():
                            self.add_document(
                                workspace_id,
                                "legal",
                                source.get("title", "source")[:150]
                                if suffix == ".pdf"
                                else "source.html",
                                path.read_bytes(),
                                origin="discovered",
                                official_url=source.get("url"),
                                extracted_pages=source["pages"],
                            )
                            break
            return self.get(workspace_id)

    def documents(self, workspace_id):
        return self.get(workspace_id).get("documents", [])

    def document(self, workspace_id, document_id):
        if not re.fullmatch(r"FILE-[a-f0-9]{24}", document_id):
            raise FileNotFoundError("Document not found.")
        if not any(doc["id"] == document_id for doc in self.documents(workspace_id)):
            raise FileNotFoundError("Document not found.")
        return json.loads(
            (self.folder(workspace_id) / "documents" / document_id / "document.json").read_text(
                encoding="utf-8"
            )
        )

    def add_document(
        self,
        workspace_id,
        collection,
        name,
        raw,
        *,
        origin="upload",
        official_url=None,
        extracted_pages=None,
        refresh=False,
        redact_personal=False,
    ):
        if collection not in ("business", "legal"):
            raise ValueError("Unknown document collection.")
        extracted = extract_document(name, raw, redact_personal=redact_personal)
        digest = hashlib.sha256(raw).hexdigest()
        with self._lock:
            workspace = self.get(workspace_id)
            documents = workspace.get("documents", [])
            duplicate = next(
                (d for d in documents if d["collection"] == collection and d["sha256"] == digest),
                None,
            )
            if duplicate and not refresh:
                return self.document(workspace_id, duplicate["id"])
            previous = [
                d
                for d in documents
                if d["collection"] == collection and d["name"] == extracted["name"]
            ]
            version = max((d["version"] for d in previous), default=0) + 1
            document_id = "FILE-" + uuid.uuid4().hex[:24]
            folder = self.folder(workspace_id) / "documents" / document_id
            folder.mkdir(parents=True)
            (folder / ("original" + extracted["suffix"])).write_bytes(raw)
            if extracted_pages is not None:
                extracted["pages"] = list(extracted_pages)
                extracted["model_pages"] = list(extracted_pages)
                extracted["method"] = "preserved-source-transcription-unverified"
            payload = {
                **extracted,
                "id": document_id,
                "workspace_id": workspace_id,
                "collection": collection,
                "sha256": digest,
                "byte_count": len(raw),
                "created_at": datetime.now(UTC).isoformat(),
                "version": version,
                "supersedes": max(previous, key=lambda d: d["version"])["id"] if previous else None,
                "context_enabled": False,
                "origin": origin,
                "official_url": official_url,
                "verification_status": "to_be_verified",
            }
            payload["page_count"] = len(payload["pages"])
            write_json(folder / "document.json", payload)
            documents.append(
                {k: v for k, v in payload.items() if k not in ("pages", "model_pages")}
            )
            workspace["documents"] = documents
            write_json(self.folder(workspace_id) / "workspace.json", workspace)
            return payload

    def refresh_extraction(
        self, workspace_id, document_id, *, redact_personal=False, retain_selection=False
    ):
        """Create a new extraction version; retain earlier text and original bytes."""
        with self._lock:
            previous = self.document(workspace_id, document_id)
            if previous["collection"] != "business":
                raise ValueError("Only business document extraction refresh is supported.")
            raw = (
                self.folder(workspace_id)
                / "documents"
                / document_id
                / ("original" + previous["suffix"])
            ).read_bytes()
            current = self.add_document(
                workspace_id,
                "business",
                previous["name"],
                raw,
                origin=previous["origin"],
                refresh=True,
                redact_personal=redact_personal,
            )
            if previous["context_enabled"]:
                self.document_context(workspace_id, document_id, False)
                if retain_selection:
                    current = self.document_context(workspace_id, current["id"], True)
            return current

    def document_context(self, workspace_id, document_id, enabled, *, redact_personal=None):
        with self._lock:
            payload = self.document(workspace_id, document_id)
            if payload["collection"] != "business":
                raise ValueError("Only company documents are profile context.")
            if (
                redact_personal is not None
                and payload.get("redact_personal", True) != redact_personal
            ):
                payload = self.refresh_extraction(
                    workspace_id, document_id, redact_personal=redact_personal
                )
                document_id = payload["id"]
            payload["context_enabled"] = bool(enabled)
            write_json(
                self.folder(workspace_id) / "documents" / document_id / "document.json", payload
            )
            workspace = self.get(workspace_id)
            workspace["documents"] = [
                {**doc, "context_enabled": bool(enabled)} if doc["id"] == document_id else doc
                for doc in workspace["documents"]
            ]
            write_json(self.folder(workspace_id) / "workspace.json", workspace)
            return payload

    def model_context(self, workspace_id):
        workspace = self.get(workspace_id)
        docs = []
        remaining = 24000
        for metadata in self.documents(workspace_id):
            if metadata["collection"] != "business" or not metadata["context_enabled"]:
                continue
            doc = self.document(workspace_id, metadata["id"])
            pages = []
            for number, text in enumerate(doc["model_pages"], 1):
                if remaining <= 0:
                    break
                pages.append({"page": number, "text": text[:remaining]})
                remaining -= len(text)
            docs.append({"id": doc["id"], "sha256": doc["sha256"], "pages": pages})
        return {
            "workspace_id": workspace_id,
            "description": workspace.get("description", ""),
            "documents": docs,
        }

    def save_profile(self, workspace_id, result):
        with self._lock:
            workspace = self.get(workspace_id)
            write_json(self.folder(workspace_id) / "profiles" / (result["id"] + ".json"), result)
            workspace["profile"] = result
            workspace["profile_history"] = workspace.get("profile_history", []) + [result["id"]]
            write_json(self.folder(workspace_id) / "workspace.json", workspace)

    def inventory_graph(self, workspace_id):
        workspace = self.get(workspace_id)
        previous = self.result(workspace_id)
        if previous:
            raw = previous["graph"]
            if raw["company_id"] != workspace_id:
                raise ValueError("Wrong workspace graph scope.")
            graph = KnowledgeGraph(workspace_id, nodes=raw["nodes"], edges=raw["edges"])
        else:
            graph = KnowledgeGraph(workspace_id)
        if workspace_id not in graph.nodes:
            graph.add_node(
                workspace_id,
                3,
                "Company",
                {"name": workspace["name"], "legal_name_confirmed": False},
            )
        for doc in self.documents(workspace_id):
            graph.add_node(
                doc["id"],
                3 if doc["collection"] == "business" else 1,
                "BusinessDocumentVersion"
                if doc["collection"] == "business"
                else "LegalDocumentVersion",
                {key: value for key, value in doc.items() if key != "context_enabled"},
            )
            graph.link(
                doc["id"],
                "BELONGS_TO" if doc["collection"] == "business" else "AVAILABLE_IN",
                workspace_id,
            )
            if doc["supersedes"] in graph.nodes:
                graph.link(doc["id"], "SUPERSEDES", doc["supersedes"])
        profile = workspace.get("profile")
        if profile:
            graph.add_node(profile["id"], 3, "BusinessUnderstanding", profile)
            graph.link(workspace_id, "HAS_PROPOSED_PROFILE", profile["id"])
            description_id = stable_id(
                "DESCRIPTION", [workspace_id, profile.get("description_snapshot", "")]
            )
            if any(fact["document_id"] == "USER-DESCRIPTION" for fact in profile["facts"]):
                graph.add_node(
                    description_id,
                    3,
                    "UserDescriptionSnapshot",
                    {"text": profile.get("description_snapshot", ""), "source": "user"},
                )
            for fact in profile["facts"]:
                target = (
                    description_id
                    if fact["document_id"] == "USER-DESCRIPTION"
                    else fact["document_id"]
                )
                graph.link(
                    profile["id"],
                    "EVIDENCED_BY",
                    target,
                    page=fact["page"],
                    quote=fact["quote"],
                    start=fact["start"],
                    end=fact["end"],
                    verification_status="to_be_verified",
                )
        payload = graph.as_dict()
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        path = self.folder(workspace_id) / "inventory-graphs" / (fingerprint + ".json")
        if not path.exists():
            write_json(path, payload)
        return payload

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
        if set(fields) - {"name", "description", "state", "progress", "runs", "latest_run"}:
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
