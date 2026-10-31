"""Local document text extraction and reviewable model-context redaction."""

import io
import re
import zipfile
from pathlib import PurePosixPath

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

MAX_TEXT = 300_000
SUPPORTED = {".txt", ".md", ".csv", ".json", ".pdf", ".docx", ".xlsx", ".html"}
PERSONAL = re.compile(
    r"họ\s*(?:và\s*)?tên|người\s*thuê|khách\s*hàng|điện\s*thoại|cccd|cmnd|hộ\s*chiếu|passport|email|địa\s*chỉ|ngày\s*sinh|tài\s*khoản|ngân\s*hàng|bank|chủ\s*hộ|thành\s*viên|liên\s*hệ",
    re.IGNORECASE,
)
# Conservative local spreadsheet projection, not an industry/category inference.
# Unknown free text remains local; values under personal headers are never sent.
OPERATIONAL_LABEL = re.compile(
    r"đơn\s*giá|giá\s*(?:điện|nước)|tiền\s*(?:điện|nước|phòng|thuê|rác)|"
    r"chỉ\s*số|số\s*(?:điện|nước|tiền|lượng|ngày|tháng|cũ|mới)|"
    r"thành\s*tiền|tổng\s*(?:tiền|cộng|thu)|kwh|m[³3]|đồng|vnd|"
    r"chi\s*phí|phí\s*(?:dịch\s*vụ|vệ\s*sinh)|thanh\s*toán|"
    r"tháng\s*\d|ngày\s*\d|kỳ\s*(?:thu|hạn)|hạng\s*mục|nội\s*dung|"
    r"unit\s*price|quantity|amount|tariff|electricity|water|total",
    re.IGNORECASE,
)
LABEL_WORDS = {
    "đơn",
    "giá",
    "điện",
    "nước",
    "tiền",
    "phòng",
    "thuê",
    "rác",
    "chỉ",
    "số",
    "lượng",
    "ngày",
    "tháng",
    "cũ",
    "mới",
    "thành",
    "tổng",
    "cộng",
    "thu",
    "kwh",
    "m",
    "m3",
    "đồng",
    "vnd",
    "chi",
    "phí",
    "dịch",
    "vụ",
    "vệ",
    "sinh",
    "thanh",
    "toán",
    "kỳ",
    "hạn",
    "hạng",
    "mục",
    "nội",
    "dung",
    "thông",
    "tin",
    "báo",
    "bảng",
    "tính",
    "hóa",
    "công",
    "nợ",
    "đã",
    "còn",
    "phải",
    "nộp",
    "từ",
    "đến",
    "trước",
    "sau",
    "sử",
    "dụng",
    "tiêu",
    "thụ",
    "đầu",
    "cuối",
    "chốt",
    "định",
    "mức",
    "hệ",
    "nhân",
    "vị",
    "stt",
    "ghi",
    "chú",
    "unit",
    "price",
    "quantity",
    "amount",
    "tariff",
    "electricity",
    "water",
    "total",
    "billing",
    "payment",
    "month",
    "rate",
}


def _spreadsheet_model_value(text):
    if PERSONAL.search(text):
        return "[nhãn/dữ liệu cá nhân đã che]"
    if re.search(r"\d{8,}", text):
        return "[chuỗi số dài giữ cục bộ; cần duyệt]"
    if re.fullmatch(r"[\d\s.,%+−*/=():;-]+", text):
        return text
    words = re.findall(r"[^\W\d_]+", text.casefold(), re.UNICODE)
    if OPERATIONAL_LABEL.search(text) and all(word in LABEL_WORDS for word in words):
        return text
    return "[văn bản tự do giữ cục bộ; cần duyệt]"


def redacted(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email đã che]", text)
    text = re.sub(r"(?<!\w)(?:\+84|0)[\d .()-]{8,17}\d(?!\w)", "[số điện thoại đã che]", text)
    text = re.sub(r"(?<!\d)\d{9,12}(?!\d)", "[mã định danh đã che]", text)
    return re.sub(
        r"(?im)^([^\n:：]*(?:họ\s*(?:và\s*)?tên|người\s*thuê|khách\s*hàng|địa\s*chỉ)[^\n:：]*[:：])[^\n]+",
        r"\1 [dữ liệu cá nhân đã che]",
        text,
    )


def _zip(raw):
    archive = zipfile.ZipFile(io.BytesIO(raw))
    entries = archive.infolist()
    if len(entries) > 2000 or sum(item.file_size for item in entries) > 100_000_000:
        archive.close()
        raise ValueError("Document exceeds extraction budget.")
    if any(item.filename.lower().endswith("vbaproject.bin") for item in entries):
        archive.close()
        raise ValueError("Macro documents are not accepted.")
    return archive


def extract_document(name, raw):
    name = name.replace("\\", "/").rsplit("/", 1)[-1].replace("\0", "")
    suffix = PurePosixPath(name).suffix.lower()
    if not name or len(name) > 180 or suffix not in SUPPORTED or not raw or len(raw) > 15_000_000:
        raise ValueError("Unsupported document or size.")
    warnings = []
    try:
        if suffix == ".pdf":
            if not raw.startswith(b"%PDF"):
                raise ValueError("Not a PDF.")
            try:
                from pypdf import PdfReader
            except ImportError:
                return {
                    "name": name,
                    "suffix": suffix,
                    "pages": [],
                    "model_pages": [],
                    "method": "pdf_reader_unavailable",
                    "status": "needs_extraction",
                    "warnings": ["Install optional pypdf for native text; original retained."],
                }
            from pypdf.errors import PyPdfError

            try:
                reader = PdfReader(io.BytesIO(raw))
                if len(reader.pages) > 250:
                    raise ValueError("PDF exceeds page budget.")
                pages = [page.extract_text() or "" for page in reader.pages]
            except PyPdfError as exc:
                raise ValueError("Could not read PDF.") from exc
            method = "pypdf-native-text"
        elif suffix == ".docx":
            with _zip(raw) as archive:
                root = ET.fromstring(archive.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                pages = [
                    "\n".join(
                        "".join(t.text or "" for t in paragraph.findall(".//w:t", ns))
                        for paragraph in root.findall(".//w:p", ns)
                    )
                ]
            method = "docx-native-text"
        elif suffix == ".xlsx":
            pages, safe_pages = _xlsx(raw)
            method = "xlsx-redacted-cells-v2"
            warnings.append("xlsx_unknown_free_text_withheld_review_original_locally")
        elif suffix == ".html":
            from rules.legal_sources import _Text

            parser = _Text()
            parser.feed(raw.decode("utf-8-sig"))
            pages = ["".join(parser.parts)]
            method = "html-native-text"
        else:
            pages = [raw.decode("utf-8-sig")]
            method = "utf8-text"
    except (
        KeyError,
        IndexError,
        zipfile.BadZipFile,
        UnicodeDecodeError,
        ET.ParseError,
        DefusedXmlException,
    ) as exc:
        raise ValueError("Could not extract this document.") from exc
    remaining, trimmed = MAX_TEXT, []
    for text in pages:
        trimmed.append(text[:remaining])
        remaining = max(0, remaining - len(text))
    if sum(map(len, pages)) > MAX_TEXT:
        warnings.append("text_budget_truncated")
    if suffix != ".xlsx":
        safe_pages = [redacted(text) for text in trimmed]
    else:
        safe_pages = [redacted(text)[:MAX_TEXT] for text in safe_pages]
    sparse = [i + 1 for i, text in enumerate(trimmed) if len(text.strip()) < 30]
    if sparse:
        warnings.append("pages_need_ocr_or_review:" + ",".join(map(str, sparse[:30])))
    result = {
        "name": name,
        "suffix": suffix,
        "pages": trimmed,
        "model_pages": safe_pages,
        "method": method,
        "status": "needs_ocr" if not any(t.strip() for t in trimmed) else "extracted",
        "warnings": warnings,
    }
    if suffix == ".xlsx":
        result["worksheets"] = [
            {"page": index, "label": f"Sheet {index}", "path": path}
            for index, path in enumerate(_xlsx_paths(raw), 1)
        ]
    return result


def _xlsx_paths(raw):
    with _zip(raw) as archive:
        return sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        )


def _xlsx(raw):
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with _zip(raw) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = [
                "".join(t.text or "" for t in item.findall(".//s:t", ns))
                for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
        names = sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        )
        if len(names) > 32:
            raise ValueError("Workbook exceeds sheet budget.")
        pages, safe_pages = [], []
        for name in names:
            root = ET.fromstring(archive.read(name))
            cells = []
            private_columns = {}
            rows = root.findall("s:sheetData/s:row", ns)
            if sum(len(row.findall("s:c", ns)) for row in rows) > 100_000:
                raise ValueError("Worksheet exceeds cell budget.")
            for row in rows:
                for cell in row.findall("s:c", ns):
                    coordinate = cell.get("r", "")
                    match = re.fullmatch(r"([A-Z]+)(\d+)", coordinate)
                    if not match:
                        continue
                    column, number = match.group(1), int(match.group(2))
                    value = cell.find("s:v", ns)
                    if cell.get("t") == "s" and value is not None:
                        text = strings[int(value.text)]
                    elif cell.get("t") == "inlineStr":
                        text = "".join(t.text or "" for t in cell.findall(".//s:t", ns))
                    else:
                        text = value.text if value is not None and value.text else ""
                    text = text[:500]
                    if PERSONAL.search(text):
                        private_columns.setdefault(column, number)
                    if text:
                        cells.append((coordinate, column, number, text))
            pages.append("\n".join(f"{coordinate}\t{text}" for coordinate, _, _, text in cells))
            operational_columns = {
                column
                for _, column, _, text in cells
                if OPERATIONAL_LABEL.search(text) and _spreadsheet_model_value(text) == text
            }
            operational_rows = {
                number
                for _, _, number, text in cells
                if OPERATIONAL_LABEL.search(text) and _spreadsheet_model_value(text) == text
            }
            safe_pages.append(
                "\n".join(
                    f"{coordinate}\t"
                    + (
                        "[dữ liệu cá nhân đã che]"
                        if column in private_columns and number > private_columns[column]
                        else "[số liệu chưa rõ nhãn; giữ cục bộ]"
                        if re.fullmatch(r"[\d\s.,%+−*/=():;-]+", text)
                        and column not in operational_columns
                        and number not in operational_rows
                        else _spreadsheet_model_value(text)
                    )
                    for coordinate, column, number, text in cells
                )
            )
    return pages, safe_pages
