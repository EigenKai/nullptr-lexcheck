"""Source/OCR boundary behavior with synthetic PDF objects and no network."""

import hashlib
import sys
from types import SimpleNamespace

from rules.legal_sources import Source
from rules.workspace_sources import WorkspaceSourceReader


def test_ocr_preserves_original_page_mapping_and_omission_gap(monkeypatch, tmp_path):
    import time

    from rules import workspace_sources

    class Writer:
        def add_page(self, page):
            pass

        def write(self, stream):
            stream.write(b"%PDF-synthetic-subset")

    monkeypatch.setitem(
        sys.modules,
        "pypdf",
        SimpleNamespace(
            PdfReader=lambda stream: SimpleNamespace(pages=list(range(6))), PdfWriter=Writer
        ),
    )
    captured = []

    class Transport:
        def complete(self, stage, payload, schema, **kwargs):
            captured.append(payload)
            return {
                "pages": [
                    {"page": i + 1, "text": "Original page " + str(original)}
                    for i, original in enumerate(payload["original_page_numbers"])
                ],
                "uncertainties": ["Unclear stamp"],
            }

    def fetch(url, **kwargs):
        pages, warnings = kwargs["ocr"](b"%PDF-synthetic-original", ("",) * 6)
        return Source("DOC-test", url, "Synthetic", "0" * 64, pages, "ocr", warnings)

    monkeypatch.setattr(workspace_sources, "fetch_source", fetch)
    reader = WorkspaceSourceReader(
        "WS-test", tmp_path, Transport(), deadline=time.monotonic() + 5, max_ocr_pages=4
    )
    result = reader("https://vanban.chinhphu.vn/example")
    assert captured[0]["original_page_numbers"] == [1, 2, 5, 6]
    assert result.pages[0] == "Original page 1"
    assert result.pages[-1] == "Original page 6"
    assert result.pages[2] == ""
    assert "ocr_page_budget_omitted:2" in result.warnings
    assert reader.remaining_ocr_pages == 0
    assert captured[0]["source_sha256"] == hashlib.sha256(b"%PDF-synthetic-original").hexdigest()


def test_bad_ocr_page_indices_never_overwrite_page_text(monkeypatch, tmp_path):
    import time

    from rules import workspace_sources

    class Writer:
        def add_page(self, page):
            pass

        def write(self, stream):
            stream.write(b"%PDF-synthetic")

    monkeypatch.setitem(
        sys.modules,
        "pypdf",
        SimpleNamespace(PdfReader=lambda stream: SimpleNamespace(pages=[1]), PdfWriter=Writer),
    )
    transport = SimpleNamespace(
        complete=lambda *args, **kwargs: {
            "pages": [{"page": 9, "text": "wrong page"}],
            "uncertainties": [],
        }
    )

    def fetch(url, **kwargs):
        pages, warnings = kwargs["ocr"](b"%PDF-synthetic", ("",))
        return Source("DOC-test", url, "Synthetic", "0" * 64, pages, "ocr", warnings)

    monkeypatch.setattr(workspace_sources, "fetch_source", fetch)
    result = WorkspaceSourceReader("WS-test", tmp_path, transport, deadline=time.monotonic() + 5)(
        "https://vanban.chinhphu.vn/example"
    )
    assert result.pages == ("",)
    assert "ocr_unavailable_pages:1" in result.warnings


def test_original_source_archive_hash_is_raw_bytes(monkeypatch, tmp_path):
    from rules import legal_sources

    raw = ("<html><p>Điều 1. Nội dung văn bản tổng hợp thử nghiệm.</p>" * 10 + "</html>").encode()

    class Response:
        def __init__(self):
            self.headers = {"Content-Type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def geturl(self):
            return "https://vanban.chinhphu.vn/example"

        def read(self, limit):
            return raw

    monkeypatch.setattr(
        legal_sources,
        "build_opener",
        lambda *args: SimpleNamespace(open=lambda *args, **kwargs: Response()),
    )
    source = legal_sources.fetch_source("https://vanban.chinhphu.vn/example", archive_dir=tmp_path)
    assert (tmp_path / (source.sha256 + ".html")).read_bytes() == raw
    assert source.sha256 == hashlib.sha256(raw).hexdigest()
