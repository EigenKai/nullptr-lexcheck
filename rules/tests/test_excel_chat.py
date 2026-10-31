"""Synthetic Excel billing, context selection and privacy regression cases."""

import hashlib
import io
import json
import zipfile
from types import SimpleNamespace
from xml.sax.saxutils import escape

from rules.documents import extract_document
from rules.workspace_chat import ConversationStore, answer
from rules.workspace_index import WorkspaceIndex
from rules.workspaces import WorkspaceStore


def billing_workbook():
    rows = {
        1: {"A": "Thông tin thu tiền", "D": "Thông tin khác"},
        11: {"A": "Họ và tên", "B": "Số tài khoản", "C": "Đơn giá điện (đồng/kWh)"},
        12: {"A": "PRIVATE SYNTHETIC TENANT", "B": "12345678", "C": "3500"},
        81: {"A": "Giá nước", "C": "15000", "D": "PRIVATE FREE TEXT"},
        82: {"C": "87654321"},
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Billing" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        cells = "".join(
            f'<row r="{row}">'
            + "".join(
                f'<c r="{column}{row}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'
                for column, text in values.items()
            )
            + "</row>"
            for row in range(1, 83)
            for values in [rows.get(row, {})]
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{cells}</sheetData></worksheet>",
        )
    return output.getvalue()


def test_excel_projection_retains_billing_cells_beyond_row_80_but_masks_private_values():
    document = extract_document("billing.xlsx", billing_workbook(), redact_personal=True)
    safe = "\n".join(document["model_pages"])
    assert "C81\t15000" in safe
    assert "C12\t3500" in safe and "Đơn giá điện" in safe
    assert "PRIVATE SYNTHETIC TENANT" not in safe and "12345678" not in safe
    assert "PRIVATE FREE TEXT" in safe and "87654321" in safe
    assert document["worksheets"][0]["page"] == 1
    assert document["worksheets"][0]["path"] == "xl/worksheets/sheet1.xml"


def test_existing_unselected_excel_is_in_inventory_and_selected_cells_have_exact_citations(
    tmp_path,
):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic billing company")
    raw = billing_workbook()
    document = store.add_document(
        workspace["id"], "business", "billing.xlsx", raw, redact_personal=True
    )
    index = WorkspaceIndex(store, workspace["id"])
    entry = next(item for item in index.inventory() if item["document_id"] == document["id"])
    assert entry["selected"] is False and entry["title"] == "billing.xlsx"
    assert not any(hit["document_id"] == document["id"] for hit in index.search("đơn giá điện"))
    store.document_context(workspace["id"], document["id"], True)
    history = ConversationStore(store)
    conversation = history.create(workspace["id"])

    class BillingClient:
        model = "synthetic"

        def generate(self, **kwargs):
            assert "PRIVATE SYNTHETIC TENANT" not in json.dumps(
                kwargs, ensure_ascii=False, default=str
            )
            if "plan" in kwargs["purpose"]:
                parsed = {"queries": ["đơn giá điện"], "read_documents": []}
            else:
                source = next(
                    source
                    for source in kwargs["payload"]["sources"]
                    if source["document_id"] == document["id"] and "C12\t3500" in source["text"]
                )
                parsed = {
                    "answer": f"Đơn giá ghi trong bảng là 3500 đồng/kWh [{source['chunk_id']}].",
                    "status": "answered",
                    "answer_type": "company_information",
                    "citations": [{"chunk_id": source["chunk_id"], "quote": "C12\t3500"}],
                }
            return SimpleNamespace(status="live", parsed=parsed, calls=1, key="synthetic")

    turn = answer(
        store, history, workspace["id"], conversation["id"], "Giá điện bao nhiêu?", BillingClient()
    )
    citation = turn["citations"][0]
    original = document["pages"][citation["page"] - 1]
    assert original[citation["start"] : citation["end"]] == citation["quote"]
    assert citation["sha256"] == hashlib.sha256(raw).hexdigest()
    assert citation["cells"] == ["C12"] and citation["worksheet"] == "Sheet 1"
    assert "CHUNK-" not in turn["answer"] and "[1]" in turn["answer"]


def test_refresh_existing_excel_preserves_previous_extraction_snapshot(tmp_path):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic company")
    original = store.add_document(workspace["id"], "business", "billing.xlsx", billing_workbook())
    refreshed = store.refresh_extraction(workspace["id"], original["id"])
    assert refreshed["id"] != original["id"] and refreshed["version"] == 2
    assert refreshed["sha256"] == original["sha256"]
    assert refreshed["supersedes"] == original["id"]
    assert refreshed["context_enabled"] is False
    assert store.document(workspace["id"], original["id"])["pages"] == original["pages"]


def test_refresh_route_is_token_protected_and_workspace_scoped(tmp_path):
    from fastapi.testclient import TestClient

    from rules.workspace_app import create_app

    store = WorkspaceStore(tmp_path)
    one, two = store.create_blank("One"), store.create_blank("Two")
    document = store.add_document(one["id"], "business", "billing.xlsx", billing_workbook())
    app = create_app(tmp_path, enabled=True)
    with TestClient(app) as client:
        path = f"/api/workspaces/{one['id']}/documents/{document['id']}/extract"
        assert client.post(path).status_code == 401
        headers = {"X-Workspace-Token": app.state.token}
        assert client.post(path.replace(one["id"], two["id"]), headers=headers).status_code == 404
        result = client.post(path, headers=headers)
        assert result.status_code == 200 and result.json()["version"] == 2
        assert result.json()["context_enabled"] is False
        assert store.documents(two["id"]) == []
