"""Same-byte extraction version and repeated spreadsheet-value regressions."""

import pytest

from rules.tests.test_workspace_chat import Client
from rules.workspace_chat import ConversationStore, answer
from rules.workspace_index import WorkspaceIndex
from rules.workspaces import WorkspaceStore


def test_same_sha_new_extraction_version_rebuilds_index_and_marks_historical_sources(
    tmp_path, monkeypatch
):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic")
    doc = store.add_document(workspace["id"], "business", "company.txt", "sửa chữa xe đạp".encode())
    store.document_context(workspace["id"], doc["id"], True)
    history = ConversationStore(store)
    thread = history.create(workspace["id"])
    answer(store, history, workspace["id"], thread["id"], "Làm gì?", Client())
    before = WorkspaceIndex(store, workspace["id"])
    original_document = store.document
    # Simulate a new extraction metadata view without modifying any old snapshot.
    monkeypatch.setattr(store, "document", lambda *args: original_document(*args) | {"version": 2})
    after = WorkspaceIndex(store, workspace["id"])
    assert after.fingerprint != before.fingerprint
    assert after.search("xe đạp")[0]["version"] == 2
    client = Client()
    answer(store, history, workspace["id"], thread["id"], "Nhắc lại?", client)
    prior = client.calls[0]["payload"]["history"][0]
    assert prior["answer"] == "Doanh nghiệp sửa chữa xe đạp."
    assert prior["source_status"] == "changed"
    assert client.calls[1]["payload"]["sources"][0]["version"] == 2
    assert history.get(workspace["id"], thread["id"])["turns"][0]["citations"][0]["version"] == 1


def test_repeated_excel_number_needs_cell_coordinate_for_exact_evidence():
    index = object.__new__(WorkspaceIndex)
    original = "A1\t3500\nC2\t3500"
    index.sources = {"FILE-synthetic": {"suffix": ".xlsx", "pages": [original]}}
    chunk = {
        "document_id": "FILE-synthetic",
        "title": "synthetic.xlsx",
        "collection": "business",
        "page": 1,
        "version": 1,
        "sha256": "synthetic",
        "text": "C2\t3500",
    }
    with pytest.raises(ValueError, match="ambiguous"):
        index.citation(chunk, "3500")
    citation = index.citation(chunk, "C2\t3500")
    assert citation["cells"] == ["C2"]
    assert original[citation["start"] : citation["end"]] == "C2\t3500"
