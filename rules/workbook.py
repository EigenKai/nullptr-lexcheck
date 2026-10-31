"""Read workbook structure locally; never project tenant cells into research."""

import hashlib
import io
import posixpath
import zipfile

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
CATEGORIES = {
    "rental_contracts": ("hợp đồng", "hop dong"),
    "electricity_water": ("điện", "nước", "dien", "nuoc"),
    "rental_billing": ("thông báo", "thong bao"),
    "fire_safety": ("pccc", "phòng cháy"),
    "residence_registration": ("tạm trú", "tam tru"),
    "deposit_settlement": ("thanh lý", "thanh ly"),
}


def summarize_workbook(raw: bytes) -> dict:
    if len(raw) > 15_000_000:
        raise ValueError("Workbook exceeds 15 MB upload budget.")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(i.file_size for i in entries) > 100_000_000:
                raise ValueError("Workbook exceeds expanded size budget.")
            if any(i.filename.lower().endswith("vbaproject.bin") for i in entries):
                raise ValueError("Macro workbooks are not accepted.")
            root = ET.fromstring(archive.read("xl/workbook.xml"))
            relations = {
                item.get("Id"): item.get("Target", "")
                for item in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
                if item.get("TargetMode") != "External"
            }
            sheets, signals = [], set()
            for index, sheet in enumerate(root.findall("s:sheets/s:sheet", NS), 1):
                if index > 32:
                    raise ValueError("Workbook exceeds 32 sheet budget.")
                name = sheet.get("name", "")
                categories = [
                    category
                    for category, terms in CATEGORIES.items()
                    if any(term in name.casefold() for term in terms)
                ]
                signals.update(categories)
                target = relations.get(sheet.get(REL), "")
                path = posixpath.normpath(
                    target.lstrip("/") if target.startswith("/") else "xl/" + target
                )
                if not path.startswith("xl/worksheets/") or not path.endswith(".xml"):
                    raise ValueError("Unsupported worksheet relation.")
                tree = ET.fromstring(archive.read(path))
                rows = tree.findall("s:sheetData/s:row", NS)
                count = sum(len(row.findall("s:c", NS)) for row in rows)
                if count > 300_000:
                    raise ValueError("Worksheet exceeds cell budget.")
                # Sheet names can also contain personal information: expose only categories.
                sheets.append(
                    {
                        "index": index,
                        "categories": categories,
                        "row_count": len(rows),
                        "cell_count": count,
                    }
                )
    except (KeyError, zipfile.BadZipFile, ET.ParseError, DefusedXmlException) as exc:
        raise ValueError("Not a supported XLSX workbook.") from exc
    if not sheets:
        raise ValueError("Workbook has no worksheets.")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "sheets": sheets,
        "signals": sorted(signals),
        "legal_name_confirmed": False,
        "sheet_presence_proves_procedure": False,
        "projection": "structure_only_no_cell_values",
        "unknown_facts": [
            "Địa phương",
            "Loại hình đăng ký kinh doanh",
            "Quy mô và kết cấu nhà",
            "Doanh thu",
            "Hồ sơ thủ tục đã thực hiện",
        ],
    }
