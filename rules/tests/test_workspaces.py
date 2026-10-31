"""Synthetic workbook and research tests: no private records, network or key."""

import io
import json
import zipfile
from datetime import date

import pytest

from rules.legal_sources import source_from_text


def workbook():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="hợp đồng" sheetId="1" r:id="rId1"/><sheet name="PCCC" sheetId="2" r:id="rId2"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>',
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>HỌ TÊN</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>PRIVATE-TENANT-0912345678</t></is></c></row></sheetData></worksheet>',
        )
        z.writestr(
            "xl/worksheets/sheet2.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>',
        )
    return output.getvalue()


def test_workbook_projects_structure_without_tenant_values():
    from rules.workbook import summarize_workbook

    manifest = summarize_workbook(workbook())
    assert len(manifest["sheets"]) == 2
    assert "rental_contracts" in manifest["signals"]
    assert "fire_safety" in manifest["signals"]
    assert "PRIVATE-TENANT" not in json.dumps(manifest)
    assert "0912345678" not in json.dumps(manifest)
    assert manifest["legal_name_confirmed"] is False
    assert manifest["sheet_presence_proves_procedure"] is False


def test_workspace_scope_private_files_and_immutable_runs(tmp_path):
    from rules.workspaces import WorkspaceStore

    store = WorkspaceStore(tmp_path)
    one = store.create("Nhà trọ ví dụ", workbook(), review_date=date(2026, 10, 31))
    two = store.create("Nhà trọ khác", workbook(), review_date=date(2026, 10, 31))
    assert one["id"] != two["id"]
    assert store.get(one["id"])["manifest"]["sha256"] == one["manifest"]["sha256"]
    assert "PRIVATE-TENANT" not in json.dumps(store.get(one["id"]))
    for bad in ("../other", "UNKNOWN", one["id"] + "/../"):
        with pytest.raises((ValueError, FileNotFoundError)):
            store.get(bad)
    graph = {"company_id": two["id"], "nodes": {}, "edges": []}
    with pytest.raises(ValueError, match="scope"):
        store.finish(one["id"], {"graph": graph})


class Transport:
    def __init__(self, *, mismatch=False, unknown_date=False):
        self.calls = []
        self.mismatch, self.unknown_date = mismatch, unknown_date
        self.events = []

    def complete(self, stage, payload, schema, **options):
        self.calls.append((stage, payload))
        if stage == "plan":
            return {"topics": [{"id": "contracts", "question": "Hợp đồng cho thuê nhà"}]}
        if stage == "search":
            return {
                "sources": [
                    {"url": "https://vanban.chinhphu.vn/example", "topic_ids": ["contracts"]}
                ]
            }
        return {
            "document_number": "1/2026/EXAMPLE",
            "relations": [],
            "proposals": [
                {
                    "topic_id": "contracts",
                    "actor": "operator",
                    "article": "Điều 1",
                    "page": 1,
                    "quote": "INVENTED" if self.mismatch else "Bên cho thuê cung cấp hợp đồng.",
                    "title": "Hồ sơ hợp đồng",
                    "concept": "Hợp đồng cho thuê",
                    "requirement": "Cần xem nội dung hợp đồng.",
                    "applicability": "Cần xác nhận loại hình nhà cho thuê.",
                    "missing_facts": ["Loại hình"],
                    "evidence_needed": ["Hợp đồng đã ký"],
                    "valid_from": None if self.unknown_date else "2026-01-01",
                    "valid_to": None,
                    "date_quote": None
                    if self.unknown_date
                    else "Luật có hiệu lực ngày 01 tháng 01 năm 2026.",
                    "date_page": None if self.unknown_date else 1,
                    "exceptions": [],
                    "related_documents": [],
                }
            ],
        }


def test_housing_research_builds_three_layers_without_static_rules(tmp_path):
    from rules.discovery import Budget
    from rules.workspace_research import research
    from rules.workspaces import WorkspaceStore

    workspace = WorkspaceStore(tmp_path).create("Ví dụ", workbook())
    transport = Transport()
    source = source_from_text(
        "https://vanban.chinhphu.vn/example",
        "Synthetic law",
        "Điều 1. Hợp đồng\nBên cho thuê cung cấp hợp đồng.\nLuật có hiệu lực ngày 01 tháng 01 năm 2026.",
    )
    result = research(
        workspace, transport, fetcher=lambda url: source, budget=Budget(max_sources=1)
    )
    assert len(result["proposals"]) == 1
    assert {n["layer"] for n in result["graph"]["nodes"].values()} == {1, 2, 3}
    proposal = result["proposals"][0]
    assert proposal["enabled"] is False
    assert proposal["verification_status"] == "to_be_verified"
    assert proposal["runtime_contract"] == "requires_domain_pack_review"
    assert proposal["quote"] == source.pages[0][proposal["quote_start"] : proposal["quote_end"]]
    assert result["executed_rule_count"] == 0
    assert result["legal_completeness_claimed"] is False
    assert "PRIVATE-TENANT" not in json.dumps(transport.calls)


@pytest.mark.parametrize("mismatch,unknown_date,expected", [(True, False, 0), (False, True, 1)])
def test_research_rejects_fake_quote_but_preserves_unknown_dates_as_pending(
    tmp_path, mismatch, unknown_date, expected
):
    from rules.discovery import Budget
    from rules.workspace_research import research
    from rules.workspaces import WorkspaceStore

    workspace = WorkspaceStore(tmp_path).create("Ví dụ", workbook())
    source = source_from_text(
        "https://vanban.chinhphu.vn/example",
        "Synthetic law",
        "Điều 1. Hợp đồng\nBên cho thuê cung cấp hợp đồng.\nLuật có hiệu lực ngày 01 tháng 01 năm 2026.",
    )
    result = research(
        workspace,
        Transport(mismatch=mismatch, unknown_date=unknown_date),
        fetcher=lambda url: source,
        budget=Budget(max_sources=1),
    )
    assert len(result["proposals"]) == expected
    if unknown_date:
        assert result["proposals"][0]["valid_from"] is None
        assert any("effective_date_missing" in gap for gap in result["gaps"])


@pytest.mark.parametrize("actor,fake_date,expected", [("tenant", False, 0), ("operator", True, 1)])
def test_operator_scope_and_date_quote_guard(tmp_path, actor, fake_date, expected):
    from rules.discovery import Budget
    from rules.workspace_research import research
    from rules.workspaces import WorkspaceStore

    class Modified(Transport):
        def complete(self, stage, payload, schema, **options):
            result = super().complete(stage, payload, schema, **options)
            if stage == "extract":
                result["proposals"][0]["actor"] = actor
                if fake_date:
                    result["proposals"][0]["valid_from"] = "2030-01-01"
            return result

    workspace = WorkspaceStore(tmp_path).create("Ví dụ", workbook())
    source = source_from_text(
        "https://vanban.chinhphu.vn/example",
        "Synthetic",
        "Điều 1. Hợp đồng\nBên cho thuê cung cấp hợp đồng.\nLuật có hiệu lực ngày 01 tháng 01 năm 2026.",
    )
    result = research(
        workspace, Modified(), fetcher=lambda url: source, budget=Budget(max_sources=1)
    )
    assert len(result["proposals"]) == expected
    if fake_date:
        assert result["proposals"][0]["valid_from"] is None
        assert (
            result["graph"]["nodes"][result["proposals"][0]["clause_id"]]["kind"] == "ClauseExcerpt"
        )


def test_workspace_reruns_never_overwrite_previous_result(tmp_path):
    from rules.workspaces import WorkspaceStore

    store = WorkspaceStore(tmp_path)
    workspace = store.create("Ví dụ", workbook())
    first = store.finish(
        workspace["id"], {"graph": {"company_id": workspace["id"]}, "marker": "first"}
    )
    first_bytes = (store.folder(workspace["id"]) / "runs" / (first + ".json")).read_bytes()
    second = store.finish(
        workspace["id"], {"graph": {"company_id": workspace["id"]}, "marker": "second"}
    )
    assert first != second
    assert (store.folder(workspace["id"]) / "runs" / (first + ".json")).read_bytes() == first_bytes
    assert store.result(workspace["id"])["marker"] == "second"
