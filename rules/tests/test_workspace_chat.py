"""Indexed workspace chat uses synthetic documents and injected model results."""

from types import SimpleNamespace

import pytest

from rules.workspaces import WorkspaceStore


@pytest.fixture
def inputs(tmp_path):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic bicycle company")
    document = store.add_document(
        workspace["id"],
        "business",
        "company.txt",
        "Doanh nghiệp sửa chữa xe đạp. Có 4 nhân viên.".encode(),
    )
    store.document_context(workspace["id"], document["id"], True)
    return store, workspace, document


def test_index_search_is_scoped_and_respects_context_revocation(inputs):
    from rules.workspace_index import WorkspaceIndex

    store, workspace, doc = inputs
    other = store.create_blank("Other company")
    other_doc = store.add_document(
        other["id"], "business", "secret.txt", b"PRIVATE-OTHER-COMPANY bicycle"
    )
    store.document_context(other["id"], other_doc["id"], True)
    index = WorkspaceIndex(store, workspace["id"])
    assert index.search("sua chua xe dap")[0]["document_id"] == doc["id"]
    assert "PRIVATE-OTHER-COMPANY" not in str(index.search("bicycle"))
    store.document_context(workspace["id"], doc["id"], False)
    refreshed = WorkspaceIndex(store, workspace["id"])
    assert not any(chunk["document_id"] == doc["id"] for chunk in refreshed.search("xe dap"))
    assert refreshed.fingerprint != index.fingerprint


class Client:
    model = "injected-model"

    def __init__(self, *, bad_quote=False):
        self.calls = []
        self.bad_quote = bad_quote

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["purpose"].startswith("workspace_chat_plan"):
            result = {"queries": ["sửa chữa xe đạp"], "read_documents": []}
        else:
            source = next(s for s in kwargs["payload"]["sources"] if s["collection"] == "business")
            result = {
                "answer": "Doanh nghiệp sửa chữa xe đạp.",
                "status": "answered",
                "answer_type": "company_information",
                "citations": [
                    {
                        "chunk_id": source["chunk_id"],
                        "quote": "FAKE" if self.bad_quote else "sửa chữa xe đạp",
                    }
                ],
            }
        return SimpleNamespace(status="live", parsed=result, key="synthetic-cache", calls=1)


def test_agent_searches_index_then_answers_with_exact_citations_and_saved_history(inputs):
    from rules.workspace_chat import ConversationStore, answer

    store, workspace, doc = inputs
    history = ConversationStore(store)
    thread = history.create(workspace["id"])
    client = Client()
    turn = answer(store, history, workspace["id"], thread["id"], "Doanh nghiệp làm gì?", client)
    assert turn["status"] == "answered"
    citation = turn["citations"][0]
    original = store.document(workspace["id"], doc["id"])["pages"][citation["page"] - 1]
    assert original[citation["start"] : citation["end"]] == citation["quote"]
    assert citation["sha256"] == doc["sha256"]
    assert {step["tool"] for step in turn["tool_trace"]} >= {"search_documents", "read_document"}
    assert turn["provenance"]["model_calls"] == 2
    assert len(history.get(workspace["id"], thread["id"])["turns"]) == 1
    assert history.list(workspace["id"])[0]["turn_count"] == 1
    assert len(client.calls) == 2


def test_fabricated_citation_is_rejected_and_not_saved_as_answer(inputs):
    from rules.workspace_chat import ConversationStore, answer

    store, workspace, _ = inputs
    history = ConversationStore(store)
    thread = history.create(workspace["id"])
    with pytest.raises(ValueError, match="quotation"):
        answer(store, history, workspace["id"], thread["id"], "Làm gì?", Client(bad_quote=True))
    assert history.get(workspace["id"], thread["id"])["turns"] == []


def test_thread_from_another_workspace_is_not_accessible(inputs):
    from rules.workspace_chat import ConversationStore

    store, workspace, _ = inputs
    history = ConversationStore(store)
    thread = history.create(workspace["id"])
    other = store.create_blank("Other")
    with pytest.raises(FileNotFoundError):
        history.get(other["id"], thread["id"])


def test_law_text_cannot_be_presented_as_company_information(tmp_path):
    from rules.workspace_chat import ConversationStore, answer

    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Unknown business")
    store.add_document(workspace["id"], "legal", "law.txt", "Điều 1. sửa chữa xe đạp".encode())
    history = ConversationStore(store)
    thread = history.create(workspace["id"])

    class WrongClient(Client):
        def generate(self, **kwargs):
            if kwargs["purpose"].startswith("workspace_chat_plan"):
                return super().generate(**kwargs)
            source = next(s for s in kwargs["payload"]["sources"] if s["collection"] == "legal")
            return SimpleNamespace(
                status="live",
                parsed={
                    "answer": "Công ty sửa xe.",
                    "status": "answered",
                    "answer_type": "company_information",
                    "citations": [{"chunk_id": source["chunk_id"], "quote": "sửa chữa xe đạp"}],
                },
                key="test",
                calls=1,
            )

    with pytest.raises(ValueError, match="company"):
        answer(store, history, workspace["id"], thread["id"], "Công ty làm gì?", WrongClient())
