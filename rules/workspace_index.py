"""Persistent per-workspace full-text tools over reviewed ingested context only."""

import hashlib
import json
import re
import sqlite3
import unicodedata


def _fold(text):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
        if unicodedata.category(c) != "Mn"
    )


class WorkspaceIndex:
    def __init__(self, store, workspace_id):
        self.store, self.workspace_id = store, workspace_id
        workspace = store.migrate_documents(workspace_id)
        self.sources = {}
        metadata = store.documents(workspace_id)
        self.documents = metadata
        for doc in metadata:
            if doc["collection"] == "business" and not doc["context_enabled"]:
                continue
            document = store.document(workspace_id, doc["id"])
            self.sources[doc["id"]] = {**document, "title": doc["name"]}
        description = workspace.get("description", "")
        if description.strip():
            from rules.documents import redacted

            self.sources["USER-DESCRIPTION"] = {
                "id": "USER-DESCRIPTION",
                "title": "Thông tin người dùng cung cấp",
                "collection": "business",
                "sha256": hashlib.sha256(description.encode()).hexdigest(),
                "version": 1,
                "pages": [description],
                "model_pages": [redacted(description)],
            }
        inventory = json.dumps(
            {
                "business_documents": sum(d["collection"] == "business" for d in metadata),
                "legal_documents": sum(d["collection"] == "legal" for d in metadata),
                "company_documents_enabled_for_model": sum(
                    d["collection"] == "business" and d["context_enabled"] for d in metadata
                ),
                "documents": [
                    {
                        "document_id": d["id"],
                        "title": d["name"],
                        "type": d.get("suffix"),
                        "collection": d["collection"],
                        "selected": d["collection"] == "legal" or d["context_enabled"],
                    }
                    for d in metadata
                ],
            },
            ensure_ascii=False,
        )
        self.sources["WORKSPACE-INVENTORY"] = {
            "id": "WORKSPACE-INVENTORY",
            "title": "Chỉ mục tài liệu của workspace",
            "collection": "metadata",
            "sha256": hashlib.sha256(inventory.encode()).hexdigest(),
            "version": 1,
            "pages": [inventory],
            "model_pages": [inventory],
        }
        material = [
            {"id": doc["id"], "sha256": doc["sha256"], "model_pages": doc["model_pages"]}
            for doc in self.sources.values()
        ]
        self.fingerprint = hashlib.sha256(
            json.dumps(material, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        self.path = store.folder(workspace_id) / "document-index.sqlite3"
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (fingerprint TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS passages (id TEXT PRIMARY KEY, payload TEXT)")
            db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(chunk_id UNINDEXED, words)"
            )
            previous = db.execute("SELECT fingerprint FROM state LIMIT 1").fetchone()
            if previous and previous[0] == self.fingerprint:
                return
            db.execute("DELETE FROM passages")
            db.execute("DELETE FROM search")
            count = 0
            for doc in self.sources.values():
                for number, text in enumerate(doc["model_pages"], 1):
                    for start in range(0, len(text), 1400):
                        if count >= 10000:
                            raise ValueError("Workspace exceeds local index budget.")
                        content = text[start : start + 1700]
                        if not content.strip():
                            continue
                        chunk_id = (
                            "CHUNK-"
                            + hashlib.sha256(
                                f"{doc['id']}:{doc['sha256']}:{number}:{start}".encode()
                            ).hexdigest()[:24]
                        )
                        payload = {
                            "chunk_id": chunk_id,
                            "document_id": doc["id"],
                            "title": doc["title"],
                            "collection": doc["collection"],
                            "sha256": doc["sha256"],
                            "version": doc["version"],
                            "page": number,
                            "text": content,
                            "worksheet": f"Sheet {number}"
                            if doc.get("suffix") == ".xlsx"
                            else None,
                        }
                        db.execute(
                            "INSERT INTO passages VALUES (?,?)",
                            (chunk_id, json.dumps(payload, ensure_ascii=False)),
                        )
                        db.execute("INSERT INTO search VALUES (?,?)", (chunk_id, _fold(content)))
                        count += 1
            db.execute("DELETE FROM state")
            db.execute("INSERT INTO state VALUES (?)", (self.fingerprint,))

    def inventory(self):
        return [
            {
                "document_id": doc["id"],
                "title": doc["name"],
                "collection": doc["collection"],
                "type": doc.get("suffix"),
                "selected": doc["collection"] == "legal" or doc["context_enabled"],
                "pages": doc["page_count"],
            }
            for doc in self.documents
        ] + [
            {
                "document_id": doc["id"],
                "title": doc["title"],
                "collection": doc["collection"],
                "pages": len(doc["model_pages"]),
                "selected": True,
            }
            for doc in self.sources.values()
            if doc["id"] not in {item["id"] for item in self.documents}
        ]

    def search(self, query, limit=6):
        terms = list(dict.fromkeys(re.findall(r"[a-z0-9]+", _fold(query))))[:20]
        if not terms:
            return []
        match = " OR ".join('"' + term + '"' for term in terms)
        with sqlite3.connect(self.path, timeout=10) as db:
            rows = db.execute(
                "SELECT p.payload FROM search s JOIN passages p ON p.id=s.chunk_id WHERE search MATCH ? ORDER BY bm25(search) LIMIT ?",
                (match, min(limit, 8)),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def read_document(self, document_id, page=1):
        if document_id not in self.sources:
            raise FileNotFoundError("Document is not in the selected workspace context.")
        with sqlite3.connect(self.path, timeout=10) as db:
            rows = db.execute("SELECT payload FROM passages").fetchall()
        return [
            json.loads(row[0])
            for row in rows
            if json.loads(row[0])["document_id"] == document_id
            and json.loads(row[0])["page"] == page
        ][:3]

    def citation(self, chunk, quote):
        source = self.sources.get(chunk["document_id"])
        if not source or not quote or quote not in chunk["text"]:
            raise ValueError("Model quotation is not in the retrieved passage.")
        original = source["pages"][chunk["page"] - 1]
        start = original.find(quote)
        if start < 0:
            raise ValueError("Model quotation is not in the original extracted text.")
        citation = {
            key: chunk[key]
            for key in ("document_id", "title", "collection", "page", "sha256", "version")
        } | {"quote": quote, "start": start, "end": start + len(quote)}
        if source.get("suffix") == ".xlsx":
            # Coordinates come from original extracted lines, never model guesses.
            line_start = original.rfind("\n", 0, start) + 1
            lines = original[line_start : start + len(quote)].splitlines()
            citation["worksheet"] = f"Sheet {chunk['page']}"
            citation["cells"] = list(
                dict.fromkeys(
                    match.group(1) for line in lines if (match := re.match(r"([A-Z]+\d+)\t", line))
                )
            )
        return citation
