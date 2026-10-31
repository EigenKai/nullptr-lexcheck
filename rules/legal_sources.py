"""Bounded official-source retrieval. Raw content is data, never instructions."""

import hashlib
import io
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urldefrag, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from rules.knowledge_graph import stable_id

OFFICIAL_DOMAINS = (
    "chinhphu.vn",
    "vbpl.vn",
    "moj.gov.vn",
    "vfa.gov.vn",
    "moh.gov.vn",
    "dichvucong.gov.vn",
    "moit.gov.vn",
)


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Only HTTPS official legal sources are allowed.")
    if not any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_DOMAINS):
        raise ValueError("Source is outside official domain allowlist.")
    return urldefrag(url)[0]


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    title: str
    sha256: str
    pages: tuple[str, ...]
    extraction_method: str


def source_from_text(url: str, title: str, text: str) -> Source:
    """Explicit text upload/test source; hash refers to UTF-8 text, not a PDF."""
    url = validate_url(url)
    digest = hashlib.sha256(text.encode()).hexdigest()
    return Source(stable_id("DOC", [url, digest]), url, title, digest, (text,), "provided_text")


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.hidden += 1
        if tag in ("p", "div", "br", "h1", "h2", "h3", "tr", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.hidden:
            self.hidden -= 1
        if tag in ("p", "div", "h1", "h2", "h3", "tr", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


class _Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_source(url: str, *, timeout_s: float = 20, max_bytes: int = 10_000_000) -> Source:
    url = validate_url(url)
    with build_opener(_Redirect()).open(
        Request(url, headers={"User-Agent": "LexCheck/0.1 source-reader"}), timeout=timeout_s
    ) as response:
        final_url = validate_url(response.geturl())
        raw = response.read(max_bytes + 1)
        content_type = response.headers.get("Content-Type", "")
    if len(raw) > max_bytes:
        raise ValueError("Source exceeds retrieval size budget.")
    if raw.startswith(b"%PDF"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError(
                "PDF extraction requires optional pypdf; use a text-bearing source or upload extracted text."
            ) from exc
        reader = PdfReader(io.BytesIO(raw))
        if len(reader.pages) > 250:
            raise ValueError("Source exceeds page budget.")
        pages = tuple(page.extract_text() or "" for page in reader.pages)
        method = "pypdf-native-text"
    else:
        if "html" not in content_type and "text/plain" not in content_type:
            raise ValueError("Unsupported official source content type.")
        parser = _Text()
        parser.feed(raw.decode("utf-8", errors="replace"))
        text = re.sub(r"[ \t]+", " ", "".join(parser.parts))
        pages, method = (re.sub(r"\n{3,}", "\n\n", text).strip(),), "html-text-v1"
    if sum(len(p.strip()) for p in pages) < 100:
        raise ValueError("Source has no usable text; OCR/source review required.")
    digest = hashlib.sha256(raw).hexdigest()
    return Source(
        stable_id("DOC", [final_url, digest]),
        final_url,
        final_url.rsplit("/", 1)[-1],
        digest,
        pages,
        method,
    )
