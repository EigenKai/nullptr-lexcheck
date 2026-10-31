"""Archive original sources; OCR only sparse PDF pages with explicit budgets."""

import base64
import hashlib
import io
import time

from pydantic import Field

from contracts.models import Contract
from rules.legal_sources import fetch_source


class OCRPage(Contract):
    page: int = Field(ge=1)
    text: str = Field(max_length=30000)


class OCRResult(Contract):
    pages: tuple[OCRPage, ...] = Field(max_length=4)
    uncertainties: tuple[str, ...] = Field(max_length=20)


class WorkspaceSourceReader:
    def __init__(
        self, workspace_id, archive_dir, transport, *, deadline, progress=None, max_ocr_pages=8
    ):
        self.workspace_id, self.archive_dir, self.transport = workspace_id, archive_dir, transport
        self.deadline, self.progress = deadline, progress or (lambda stage, message: None)
        self.remaining_ocr_pages = max_ocr_pages

    def __call__(self, url):
        def transcribe(raw, pages):
            from pypdf import PdfReader, PdfWriter

            sparse = [i for i, page in enumerate(pages) if len(page.strip()) < 50]
            # Include the closing pages, where effectivity is often stated, within the budget.
            priority = list(dict.fromkeys(sparse[:2] + sparse[-2:] + sparse[2:-2]))
            selected = priority[: self.remaining_ocr_pages]
            warnings = (
                [f"ocr_page_budget_omitted:{len(sparse) - len(selected)}"]
                if len(selected) < len(sparse)
                else []
            )
            result = list(pages)
            reader = PdfReader(io.BytesIO(raw))
            for offset in range(0, len(selected), 4):
                remaining = self.deadline - time.monotonic()
                if remaining <= 1:
                    warnings.append("ocr_time_budget_exhausted")
                    break
                indices = selected[offset : offset + 4]
                self.remaining_ocr_pages -= len(indices)
                writer = PdfWriter()
                for index in indices:
                    writer.add_page(reader.pages[index])
                data = io.BytesIO()
                writer.write(data)
                self.progress(
                    "ocr",
                    f"Đang OCR {len(indices)} trang scan bằng LLM; bản gốc được giữ cục bộ để đối chiếu.",
                )
                try:
                    response = OCRResult.model_validate(
                        self.transport.complete(
                            "ocr",
                            {
                                "workspace_id": self.workspace_id,
                                "source_url": url,
                                "source_sha256": hashlib.sha256(raw).hexdigest(),
                                "original_page_numbers": [i + 1 for i in indices],
                                "pdf_base64": base64.b64encode(data.getvalue()).decode(),
                            },
                            OCRResult.model_json_schema(),
                            timeout_s=min(90, remaining),
                        )
                    )
                    if sorted(p.page for p in response.pages) != list(range(1, len(indices) + 1)):
                        raise ValueError("OCR did not preserve page boundaries.")
                    for page in response.pages:
                        result[indices[page.page - 1]] = page.text
                    warnings.extend("ocr_uncertainty:" + item for item in response.uncertainties)
                except (ValueError, RuntimeError, TimeoutError):
                    warnings.append(
                        "ocr_unavailable_pages:" + ",".join(str(i + 1) for i in indices)
                    )
            return tuple(result), tuple(warnings)

        return fetch_source(
            url,
            timeout_s=min(20, max(1, self.deadline - time.monotonic())),
            archive_dir=self.archive_dir,
            ocr=transcribe,
        )
