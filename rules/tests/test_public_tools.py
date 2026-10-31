import httpx
import pytest

from rules.public_tools import PublicFiles
from rules.workspace_index import WorkspaceIndex
from rules.workspaces import WorkspaceStore


def test_open_url_reads_actual_html_and_resolves_download_links(tmp_path):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic public tool test")
    raw = b'<html><body><p>Actual source text with free content.</p><a href="/source.pdf">PDF</a></body></html>'
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=raw, headers={"content-type": "text/html"})
        )
    ) as client:
        files = PublicFiles(
            WorkspaceIndex(store, workspace["id"]),
            http_client=client,
            resolver=lambda *args, **kwargs: [(None, None, None, None, ("8.8.8.8", 443))],
        )
        result = files.open_url("https://example.org/page")
    assert result["status"] == "read" and result["parser"] == "html-native-text"
    assert "Actual source text" in result["sources"][0]["text"]
    assert result["links"] == ["https://example.org/source.pdf"]
    assert result["sha256"] and result["retrieved_at"]
    other = store.create_blank("Other")
    with pytest.raises(FileNotFoundError):
        PublicFiles(WorkspaceIndex(store, other["id"])).read_file(result["file_id"])


def test_public_download_denies_private_redirect_without_contacting_destination(tmp_path):
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic redirect test")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
        )
    ) as client:
        files = PublicFiles(
            WorkspaceIndex(store, workspace["id"]),
            http_client=client,
            resolver=lambda *args, **kwargs: [(None, None, None, None, ("8.8.8.8", 443))],
        )
        with pytest.raises(ValueError, match="Private/local"):
            files.download_file("https://example.org/page")
