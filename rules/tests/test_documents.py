"""Generic document intake: synthetic private records only; no network/model."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from rules.tests.test_workspaces import workbook
from rules.workspace_app import create_app
from rules.workspaces import WorkspaceStore


def test_two_collections_are_persisted_and_scoped_with_immutable_versions(tmp_path):
    store = WorkspaceStore(tmp_path)
    one = store.create_blank("Company One", description="Business description from user")
    two = store.create_blank("Company Two")
    company = store.add_document(one["id"], "business", "company.txt", b"Company record")
    law = store.add_document(one["id"], "legal", "law.txt", b"Article 1. Synthetic law")
    assert company["collection"] == "business" and law["collection"] == "legal"
    assert company["context_enabled"] is False
    assert store.documents(two["id"]) == []
    assert len(store.documents(one["id"])) == 2
    assert (
        store.add_document(one["id"], "business", "company.txt", b"Company record")["id"]
        == company["id"]
    )
    revised = store.add_document(one["id"], "business", "company.txt", b"Company revised")
    assert revised["version"] == 2 and revised["supersedes"] == company["id"]
    assert store.document(one["id"], company["id"])["pages"] == ["Company record"]
    graph = store.inventory_graph(one["id"])
    assert graph["nodes"][company["id"]]["layer"] == 3
    assert graph["nodes"][law["id"]]["layer"] == 1
    assert not any(node["layer"] == 2 for node in graph["nodes"].values())
    with pytest.raises(FileNotFoundError):
        store.document(two["id"], company["id"])


def test_redacted_preview_is_local_and_model_context_is_opt_in(tmp_path):
    store = WorkspaceStore(tmp_path)
    w = store.create_blank("Private example")
    doc = store.add_document(
        w["id"],
        "business",
        "record.txt",
        "Họ tên: PRIVATE PERSON\nEmail: private@example.invalid\nĐiện thoại: 0912345678\nHoạt động: cho thuê phòng".encode(),
        redact_personal=True,
    )
    assert "PRIVATE PERSON" in doc["pages"][0]
    assert "PRIVATE PERSON" not in doc["model_pages"][0]
    assert "private@example.invalid" not in doc["model_pages"][0]
    assert store.model_context(w["id"])["documents"] == []
    store.document_context(w["id"], doc["id"], True)
    context = store.model_context(w["id"])
    assert context["documents"][0]["id"] == doc["id"]
    assert "0912345678" not in json.dumps(context)
    store.add_document(w["id"], "legal", "law.txt", b"LEGAL-SENTINEL")
    assert "LEGAL-SENTINEL" not in json.dumps(store.model_context(w["id"]))


def test_real_upload_api_supports_existing_workspace_and_json_creation(tmp_path):
    app = create_app(tmp_path, enabled=True)
    headers = {"X-Workspace-Token": app.state.token}
    with TestClient(app) as client:
        w = client.post(
            "/api/workspaces",
            headers=headers,
            json={"name": "Any company", "description": "User-supplied activity"},
        )
        assert w.status_code == 201
        workspace_id = w.json()["id"]
        for collection in ("business", "legal"):
            response = client.post(
                f"/api/workspaces/{workspace_id}/documents/{collection}",
                headers={**headers, "X-File-Name": "document.txt"},
                content=b"Synthetic source text",
            )
            assert response.status_code == 201
            assert response.json()["collection"] == collection
        docs = client.get(f"/api/workspaces/{workspace_id}/documents", headers=headers).json()
        assert {d["collection"] for d in docs} == {"business", "legal"}
        assert (
            client.post(
                f"/api/workspaces/{workspace_id}/documents/legal",
                headers={**headers, "X-File-Name": "unsafe.exe"},
                content=b"MZ",
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/workspaces/{workspace_id}/profile", headers=headers, json={"live": True}
            ).status_code
            == 503
        )


def test_migrated_official_html_keeps_original_bytes_hash(tmp_path):
    store = WorkspaceStore(tmp_path)
    workspace = store.create("Legacy example", workbook())
    raw = b"<html><p>Synthetic official source.</p><script>ignored()</script></html>"
    digest = hashlib.sha256(raw).hexdigest()
    folder = store.folder(workspace["id"]) / "sources"
    folder.mkdir()
    (folder / (digest + ".html")).write_bytes(raw)
    store.finish(
        workspace["id"],
        {
            "graph": {
                "company_id": workspace["id"],
                "nodes": {
                    "DOC-test": {
                        "kind": "LegalDoc",
                        "layer": 1,
                        "payload": {
                            "sha256": digest,
                            "url": "https://vanban.chinhphu.vn/example",
                            "title": "example",
                            "pages": ["Synthetic official source."],
                        },
                    }
                },
                "edges": [],
            }
        },
    )
    store.migrate_documents(workspace["id"])
    law = next(doc for doc in store.documents(workspace["id"]) if doc["collection"] == "legal")
    assert law["sha256"] == digest
    assert (
        store.folder(workspace["id"]) / "documents" / law["id"] / "original.html"
    ).read_bytes() == raw
