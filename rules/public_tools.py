"""Independent public URL/download/native-file tools scoped to one workspace."""

import hashlib
import io
import ipaddress
import json
import re
import socket
import zipfile
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

import httpx

from rules.documents import extract_document


def public_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme not in ("http", "https")
        or not host
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 80, 443)
    ):
        raise ValueError("Use a public HTTP(S) URL without credentials or private ports.")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "%" in host:
        raise ValueError("Private/local URL is not accessible.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise ValueError("Private/local URL is not accessible.") from None
    else:
        if not address.is_global:
            raise ValueError("Private/local URL is not accessible.")
    return urldefrag(url)[0]


class _Links(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.links = base, []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            try:
                link = public_url(urljoin(self.base, href))
            except ValueError:
                return
            if link not in self.links and len(self.links) < 100:
                self.links.append(link)


class PublicFiles:
    def __init__(self, index, *, http_client=None, resolver=socket.getaddrinfo):
        self.index, self.client, self.resolver = index, http_client, resolver
        self.folder = index.store.folder(index.workspace_id) / "chat-downloads"
        self.folder.mkdir(parents=True, exist_ok=True)

    def download_file(self, url):
        url = public_url(url)
        client = self.client or httpx.Client(follow_redirects=False, trust_env=False)
        try:
            for _ in range(4):
                parsed = urlparse(url)
                addresses = self.resolver(
                    parsed.hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
                ips = [entry[4][0] for entry in addresses]
                if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
                    raise ValueError("Private/local network destination is not accessible.")
                # Pin the verified public address while retaining original Host/TLS SNI.
                pinned = httpx.URL(url).copy_with(host=ips[0])
                with client.stream(
                    "GET",
                    pinned,
                    headers={"Host": parsed.netloc, "User-Agent": "LexCheck-public-reader/1.0"},
                    extensions={"sni_hostname": parsed.hostname},
                    timeout=25,
                ) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = public_url(urljoin(url, response.headers.get("location", "")))
                        continue
                    response.raise_for_status()
                    raw = bytearray()
                    for part in response.iter_bytes():
                        raw.extend(part)
                        if len(raw) > 15_000_000:
                            raise ValueError("Download exceeds 15 MB file budget.")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                break
            else:
                raise ValueError("Too many public redirects.")
        finally:
            if self.client is None:
                client.close()
        digest = hashlib.sha256(raw).hexdigest()
        file_id = "WEB-" + hashlib.sha256((url + digest).encode()).hexdigest()[:24]
        metadata = {
            "file_id": file_id,
            "url": url,
            "sha256": digest,
            "bytes": len(raw),
            "content_type": content_type,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        (self.folder / (file_id + ".bin")).write_bytes(raw)
        (self.folder / (file_id + ".json")).write_text(json.dumps(metadata), encoding="utf-8")
        return {
            **metadata,
            "status": "downloaded",
            "note": "Bytes archived; content has not been read yet.",
        }

    def read_file(self, file_id, page=1, offset=0, query=None):
        if file_id in self.index.sources and not file_id.startswith("WEB-"):
            return {"sources": self.index.read_document(file_id, page)}
        if not re.fullmatch(r"WEB-[a-f0-9]{24}", file_id):
            raise FileNotFoundError("File is not selected or downloaded in this workspace.")
        metadata = json.loads((self.folder / (file_id + ".json")).read_text(encoding="utf-8"))
        raw = (self.folder / (file_id + ".bin")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
            raise ValueError("Downloaded bytes changed.")
        kind = metadata["content_type"]
        if raw.startswith(b"%PDF"):
            suffix = ".pdf"
        elif raw.startswith(b"PK"):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                suffix = (
                    ".docx"
                    if "word/document.xml" in archive.namelist()
                    else ".xlsx"
                    if "xl/workbook.xml" in archive.namelist()
                    else None
                )
            if suffix is None:
                raise ValueError("Unsupported downloaded archive format.")
        elif "html" in kind or raw.lstrip().lower().startswith((b"<!doctype html", b"<html")):
            suffix = ".html"
        elif kind.startswith("text/") or kind == "application/json":
            suffix = ".txt"
        else:
            raise ValueError("Downloaded format is not a supported text/PDF/Word/Excel document.")
        extracted = extract_document("downloaded-source" + suffix, raw, redact_personal=False)
        pages = extracted["pages"]
        if not 1 <= page <= len(pages):
            return {
                **metadata,
                "status": extracted["status"],
                "page_count": len(pages),
                "sources": [],
                "warnings": extracted["warnings"],
            }
        text = pages[page - 1]
        if query and (position := text.casefold().find(query.casefold())) >= 0:
            offset = max(0, position - 500)
        if not 0 <= offset <= len(text):
            raise ValueError("Unknown text offset.")
        source = {
            **extracted,
            "id": file_id,
            "title": metadata["url"],
            "collection": "web",
            "version": 1,
            "sha256": metadata["sha256"],
            "source_url": metadata["url"],
            "retrieved_at": metadata["retrieved_at"],
        }
        self.index.sources[file_id] = source
        chunk = {
            "chunk_id": "CHUNK-"
            + hashlib.sha256(f"{file_id}:{page}:{offset}".encode()).hexdigest()[:24],
            "document_id": file_id,
            "title": metadata["url"],
            "collection": "web",
            "version": 1,
            "sha256": metadata["sha256"],
            "page": page,
            "text": text[offset : offset + 12000],
        }
        links = _Links(metadata["url"])
        if suffix == ".html":
            links.feed(raw.decode("utf-8", errors="replace"))
        return {
            **metadata,
            "status": "read" if text.strip() else "needs_ocr_or_review",
            "parser": extracted["method"],
            "page": page,
            "page_count": len(pages),
            "offset": offset,
            "next_offset": offset + 12000 if len(text) > offset + 12000 else None,
            "sources": [chunk] if text.strip() else [],
            "links": links.links,
            "warnings": extracted["warnings"],
        }

    def open_url(self, url):
        downloaded = self.download_file(url)
        return self.read_file(downloaded["file_id"])
