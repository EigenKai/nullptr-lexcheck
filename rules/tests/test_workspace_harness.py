"""Optional OSS tool runner tests; generated documents and injected clients only."""

import io
import json
import re
import zipfile
from types import SimpleNamespace

import pytest

pytest.importorskip("smolagents")
openpyxl = pytest.importorskip("openpyxl")

from rules.workspace_chat import ConversationStore, answer
from rules.workspaces import WorkspaceStore


def company(tmp_path):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet["A1"], sheet["A2"] = "Đơn giá điện (đồng/kWh)", 3500
    sheet["B1"], sheet["B2"] = "Họ tên", "PRIVATE SYNTHETIC PERSON"
    output = io.BytesIO()
    workbook.save(output)
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic company")
    document = store.add_document(workspace["id"], "business", "billing.xlsx", output.getvalue())
    store.document_context(workspace["id"], document["id"], True)
    return store, workspace, document


class ToolModel:
    model = "injected-harness-model"

    def __init__(self, document_id):
        self.document_id, self.calls = document_id, []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        assert "PRIVATE" not in json.dumps(kwargs, default=str)
        action = {
            "tool": "read_excel",
            "query": None,
            "document_id": self.document_id,
            "page": 1,
            "cell_range": "A1:A2",
            "final": None,
        }
        if len(self.calls) > 1:
            # The test model reacts to the actual tool observation, not fixture answer text.
            text = json.dumps(kwargs["payload"], ensure_ascii=False)
            assert "3500" in text and "openpyxl" in text
            chunk_id = re.findall(r"CHUNK-[a-f0-9]{24}", text)[-1]
            action = {
                "tool": "final_answer",
                "query": None,
                "document_id": None,
                "page": 1,
                "cell_range": None,
                "final": {
                    "answer": "Giá ghi trong bảng là 3500 đồng/kWh.",
                    "status": "answered",
                    "answer_type": "company_information",
                    "citations": [{"chunk_id": chunk_id, "quote": "A2\t3500"}],
                },
            }
        return SimpleNamespace(status="live", parsed=action, calls=1, key="synthetic")


def test_real_oss_runner_selects_native_excel_tool_then_cites_reviewed_cell(tmp_path, monkeypatch):
    monkeypatch.setenv("LEXCHECK_WORKSPACE_TOOL_HARNESS_ENABLED", "1")
    store, workspace, document = company(tmp_path)
    conversations = ConversationStore(store)
    conversation = conversations.create(workspace["id"])
    client = ToolModel(document["id"])
    turn = answer(store, conversations, workspace["id"], conversation["id"], "Giá điện?", client)
    assert turn["status"] == "answered" and turn["citations"][0]["cells"] == ["A2"]
    assert turn["provenance"]["harness"] == "smolagents.ToolCallingAgent"
    assert turn["provenance"]["model_calls"] == 2
    assert any(
        step["tool"] == "read_excel" and step.get("provider") == "openpyxl"
        for step in turn["tool_trace"]
    )
    assert len(client.calls) == 2


def test_tools_deny_other_workspace_and_unselected_documents(tmp_path):
    from rules.workspace_harness import WorkspaceTools
    from rules.workspace_index import WorkspaceIndex

    store, workspace, document = company(tmp_path)
    other = store.create_blank("Other")
    tools = WorkspaceTools(WorkspaceIndex(store, other["id"]))
    with pytest.raises(FileNotFoundError):
        tools.read_excel(document["id"], 1, "A1:A2")
    store.document_context(workspace["id"], document["id"], False)
    tools = WorkspaceTools(WorkspaceIndex(store, workspace["id"]))
    with pytest.raises(FileNotFoundError):
        tools.read_document(document["id"], 1)


def test_search_tool_uses_actual_provider_urls_and_refuses_private_query(tmp_path, monkeypatch):
    from rules.workspace_harness import WorkspaceTools
    from rules.workspace_index import WorkspaceIndex

    store, workspace, _ = company(tmp_path)
    calls = []

    def unavailable(*args, **kwargs):
        raise ValueError("Synthetic unavailable source; no network in tests.")

    monkeypatch.setattr("rules.workspace_harness.fetch_source", unavailable)

    class Search:
        def complete(self, stage, payload, schema, **options):
            calls.append((stage, payload, options))
            return {
                "sources": [{"url": "https://vanban.chinhphu.vn/example", "topic_ids": ["chat"]}]
            }

    tools = WorkspaceTools(WorkspaceIndex(store, workspace["id"]), search=Search())
    result = tools.web_search("quy định giá điện cho người thuê nhà")
    assert result["search_leads"][0]["url"] == "https://vanban.chinhphu.vn/example"
    assert result["sources"] == []
    assert calls[0][0] == "search" and calls[0][2]["web_search"] is True
    with pytest.raises(ValueError, match="private"):
        tools.web_search("email private@example.invalid")
    with pytest.raises(ValueError, match="budget"):
        tools.web_search("public topic")


def test_runner_stops_at_budget_without_saving_fake_final(tmp_path, monkeypatch):
    from rules.workspace_harness import run
    from rules.workspace_index import WorkspaceIndex

    store, workspace, document = company(tmp_path)
    client = ToolModel(document["id"])
    client.generate = lambda **kwargs: SimpleNamespace(
        status="live",
        parsed={
            "tool": "search_documents",
            "query": "điện",
            "document_id": None,
            "page": 1,
            "cell_range": None,
            "final": None,
        },
        calls=1,
        key="repeat",
    )
    with pytest.raises(RuntimeError, match="budget"):
        run(WorkspaceIndex(store, workspace["id"]), {"question": "giá điện"}, client, max_steps=2)


def test_native_excel_retains_legal_collection_and_cannot_prove_company_facts(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("LEXCHECK_WORKSPACE_TOOL_HARNESS_ENABLED", "1")
    workbook = openpyxl.Workbook()
    workbook.active["A1"], workbook.active["A2"] = "Unit price", 3500
    output = io.BytesIO()
    workbook.save(output)
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Unknown company")
    document = store.add_document(workspace["id"], "legal", "law.xlsx", output.getvalue())
    conversations = ConversationStore(store)
    conversation = conversations.create(workspace["id"])
    with pytest.raises(ValueError, match="company information"):
        answer(
            store,
            conversations,
            workspace["id"],
            conversation["id"],
            "Unit price?",
            ToolModel(document["id"]),
        )
    assert conversations.get(workspace["id"], conversation["id"])["turns"] == []


def test_native_excel_limits_ranges_and_does_not_expose_unreviewed_cells(tmp_path):
    from rules.workspace_harness import WorkspaceTools
    from rules.workspace_index import WorkspaceIndex

    store, workspace, document = company(tmp_path)
    tools = WorkspaceTools(WorkspaceIndex(store, workspace["id"]))
    with pytest.raises(ValueError, match="100-cell"):
        tools.read_excel(document["id"], 1, "A1:K10")
    result = tools.read_excel(document["id"], 1, "A1:B2")
    assert "PRIVATE" not in json.dumps(result)
    assert "A2\t3500" in result["sources"][0]["text"]


@pytest.mark.parametrize("suffix", [".docx", ".pdf"])
def test_actual_document_ingestion_and_oss_read_tool_return_exact_evidence(tmp_path, suffix):
    from rules.workspace_harness import run
    from rules.workspace_index import WorkspaceIndex

    output = io.BytesIO()
    evidence = "Synthetic service record: 7 units."
    if suffix == ".docx":
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'
                + evidence
                + "</w:t></w:r></w:p></w:body></w:document>",
            )
    else:
        pypdf = pytest.importorskip("pypdf")
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        writer = pypdf.PdfWriter()
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 20 700 Td ({evidence}) Tj ET".encode())
        page[NameObject("/Contents")] = stream
        writer.write(output)
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic document company")
    document = store.add_document(workspace["id"], "business", "record" + suffix, output.getvalue())
    store.document_context(workspace["id"], document["id"], True)

    class Reader:
        model = "injected-document-reader"
        calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            action = {
                "tool": "read_document",
                "query": None,
                "document_id": document["id"],
                "page": 1,
                "cell_range": None,
                "final": None,
            }
            if self.calls == 2:
                text = json.dumps(kwargs["payload"], ensure_ascii=False)
                assert evidence in text
                action.update(
                    tool="final_answer",
                    final={
                        "answer": evidence,
                        "status": "answered",
                        "answer_type": "company_information",
                        "citations": [
                            {
                                "chunk_id": re.findall(r"CHUNK-[a-f0-9]{24}", text)[-1],
                                "quote": evidence,
                            }
                        ],
                    },
                )
            return SimpleNamespace(status="live", parsed=action, calls=1, key="document")

    index = WorkspaceIndex(store, workspace["id"])
    draft, chunks, trace, provenance = run(
        index, {"question": "Read the selected record."}, Reader()
    )
    assert index.citation(chunks[0], draft.citations[0].quote)["quote"] == evidence
    assert trace[0]["tool"] == "read_document" and provenance["model_calls"] == 2


def test_public_search_flag_is_required_even_with_injected_provider(tmp_path, monkeypatch):
    from rules.workspace_harness import run
    from rules.workspace_index import WorkspaceIndex

    monkeypatch.delenv("LEXCHECK_WORKSPACE_WEB_SEARCH_ENABLED", raising=False)
    store, workspace, _ = company(tmp_path)

    class NoSearch:
        def complete(self, *args, **kwargs):
            raise AssertionError("Default-off public search was called.")

    class Final:
        model = "injected-gate"

        def generate(self, **kwargs):
            assert "web_search" not in kwargs["payload"]["tools"]
            return SimpleNamespace(
                status="live",
                calls=1,
                key="gate",
                parsed={
                    "tool": "final_answer",
                    "query": None,
                    "document_id": None,
                    "page": 1,
                    "cell_range": None,
                    "final": {
                        "answer": "Missing relevant legal evidence.",
                        "status": "not_enough_information",
                        "answer_type": "unknown",
                        "citations": [],
                    },
                },
            )

    draft, _, trace, provenance = run(
        WorkspaceIndex(store, workspace["id"]),
        {"question": "Current law?"},
        Final(),
        search=NoSearch(),
    )
    assert draft.status == "not_enough_information" and not trace
    assert provenance["public_search_requests"] == 0


def test_real_oss_search_observation_is_ingested_cited_and_counts_all_model_calls(
    tmp_path, monkeypatch
):
    import hashlib

    from rules.legal_sources import Source

    monkeypatch.setenv("LEXCHECK_WORKSPACE_TOOL_HARNESS_ENABLED", "1")
    monkeypatch.setenv("LEXCHECK_WORKSPACE_WEB_SEARCH_ENABLED", "1")
    evidence = "Article 1. Synthetic public rule requires a source review."
    raw = ("<html><body><p>" + evidence + "</p></body></html>").encode()
    digest = hashlib.sha256(raw).hexdigest()
    url = "https://vanban.chinhphu.vn/synthetic-source"

    def fetch(url, **kwargs):
        archive = kwargs["archive_dir"]
        archive.mkdir(parents=True, exist_ok=True)
        (archive / (digest + ".html")).write_bytes(raw)
        return Source("DOC-synthetic", url, "Synthetic", digest, (evidence,), "html-text-v1")

    monkeypatch.setattr("rules.workspace_harness.fetch_source", fetch)

    class Search:
        def __init__(self):
            self.events = []

        def complete(self, *args, **kwargs):
            self.events.append(
                {
                    "stage": "search",
                    "cached": False,
                    "model": "injected-search",
                    "response_id": "synthetic-response",
                }
            )
            return {"sources": [{"url": url, "topic_ids": ["chat"]}]}

    # Inject the public-provider boundary, while keeping the real OSS loop and
    # WorkspaceStore/FTS ingestion/citation validation intact.
    monkeypatch.setattr("detect.client.DiscoveryTransport", lambda **kwargs: Search())

    class Researcher:
        model = "injected-researcher"
        calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            action = {
                "tool": "web_search",
                "query": "synthetic public rule",
                "document_id": None,
                "page": 1,
                "cell_range": None,
                "final": None,
            }
            if self.calls == 2:
                text = json.dumps(kwargs["payload"], ensure_ascii=False)
                assert evidence in text and "ingested_unverified" in text
                action.update(
                    tool="final_answer",
                    final={
                        "answer": evidence,
                        "status": "answered",
                        "answer_type": "legal_reference",
                        "citations": [
                            {
                                "chunk_id": re.findall(r"CHUNK-[a-f0-9]{24}", text)[-1],
                                "quote": evidence,
                            }
                        ],
                    },
                )
            return SimpleNamespace(status="live", parsed=action, calls=1, key="research")

    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic public research")
    history = ConversationStore(store)
    thread = history.create(workspace["id"])
    turn = answer(
        store,
        history,
        workspace["id"],
        thread["id"],
        "Read the synthetic public rule.",
        Researcher(),
    )
    citation = turn["citations"][0]
    assert citation["official_url"] == url and citation["sha256"] == digest
    assert citation["collection"] == "legal" and citation["verification_status"] == "to_be_verified"
    source = store.document(workspace["id"], citation["document_id"])
    assert source["pages"][0][citation["start"] : citation["end"]] == evidence
    assert turn["provenance"]["model_calls"] == 3
    assert turn["provenance"]["agent_model_calls"] == 2
    assert turn["provenance"]["public_search_model_calls"] == 1


def test_context_revoked_after_tool_is_not_forwarded_to_next_model_call(tmp_path, monkeypatch):
    from rules.workspace_harness import WorkspaceTools, run
    from rules.workspace_index import WorkspaceIndex

    store, workspace, document = company(tmp_path)
    original = WorkspaceTools.read_excel

    def revoke_after_read(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        store.document_context(workspace["id"], document["id"], False)
        return result

    monkeypatch.setattr(WorkspaceTools, "read_excel", revoke_after_read)
    client = ToolModel(document["id"])
    with pytest.raises(RuntimeError, match="unavailable"):
        run(WorkspaceIndex(store, workspace["id"]), {"question": "Read unit price"}, client)
    assert len(client.calls) == 1


def test_workbook_overview_reads_all_seven_reviewed_sheets_without_legal_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("LEXCHECK_WORKSPACE_TOOL_HARNESS_ENABLED", "1")
    monkeypatch.setenv("LEXCHECK_WORKSPACE_WEB_SEARCH_ENABLED", "1")
    book = openpyxl.Workbook()
    book.remove(book.active)
    for page in range(1, 8):
        sheet = book.create_sheet("Private name " + str(page))
        sheet["A1"], sheet["A2"] = "Unit price", 3000 + page
        sheet["B1"], sheet["B2"] = "Họ tên", "PRIVATE PERSON"
    output = io.BytesIO()
    book.save(output)
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic summary")
    document = store.add_document(workspace["id"], "business", "seven.xlsx", output.getvalue())
    store.document_context(workspace["id"], document["id"], True)

    class SummaryModel:
        model = "injected-summary"
        calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            assert "summarize_excel" in kwargs["payload"]["tools"]
            action = {
                "tool": "summarize_excel",
                "query": None,
                "document_id": document["id"],
                "page": 1,
                "cell_range": None,
                "final": None,
            }
            if self.calls == 2:
                text = json.dumps(kwargs["payload"], ensure_ascii=False)
                assert "PRIVATE" not in text and "Private name" not in text
                assert "3007" in text and "Sheet 7" in text and "sampled_reviewed_cells" in text
                chunk_id = re.findall(r"CHUNK-[a-f0-9]{24}", text)[-1]
                action.update(
                    tool="final_answer",
                    final={
                        "answer": "Tóm tắt phần đã đọc: bảng có đơn giá 3007 trên Sheet 7. Đây là mẫu nội dung đã che, chưa phải toàn bộ dữ liệu.",
                        "status": "answered",
                        "answer_type": "company_information",
                        "citations": [{"chunk_id": chunk_id, "quote": "A2\t3007"}],
                    },
                )
            return SimpleNamespace(status="live", parsed=action, calls=1, key="summary")

    history = ConversationStore(store)
    conversation = history.create(workspace["id"])
    turn = answer(
        store,
        history,
        workspace["id"],
        conversation["id"],
        "Tóm tắt nội dung file Excel đã chọn",
        SummaryModel(),
    )
    assert turn["status"] == "answered" and turn["citations"][0]["page"] == 7
    assert turn["provenance"]["model_calls"] == 2
    assert turn["provenance"]["public_search_requests"] == 0
    assert any(step.get("worksheets_covered") == 7 for step in turn["tool_trace"])


def test_invalid_summary_quote_can_be_repaired_inside_remaining_agent_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("LEXCHECK_WORKSPACE_TOOL_HARNESS_ENABLED", "1")
    store, workspace, document = company(tmp_path)

    class RepairModel(ToolModel):
        def generate(self, **kwargs):
            result = super().generate(**kwargs)
            if len(self.calls) == 2:
                result.parsed["final"]["citations"][0]["quote"] += "\u2063"
            return result

    client = RepairModel(document["id"])
    history = ConversationStore(store)
    conversation = history.create(workspace["id"])
    turn = answer(
        store, history, workspace["id"], conversation["id"], "Summarize selected workbook", client
    )
    assert turn["status"] == "answered" and turn["provenance"]["model_calls"] == 3
    assert turn["citations"][0]["quote"] == "A2\t3500"
