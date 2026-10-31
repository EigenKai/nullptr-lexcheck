"""Actual HTTP adapter contract with injected HTTP and synthetic credentials only."""

import httpx
import pytest

from rules.brave_search import BraveSearch, validate_public_url


def test_brave_keeps_public_nonofficial_results_and_allows_repeated_searches():
    requests = []

    def respond(request):
        requests.append(request)
        assert request.headers["X-Subscription-Token"] == "synthetic-key"
        assert "site:" not in request.url.params["q"]
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Python guide",
                            "url": "https://docs.python.org/3/tutorial/",
                            "description": "Actual provider snippet",
                            "extra_snippets": ["Additional provider text"],
                        },
                        {
                            "title": "Other public result",
                            "url": "https://example.org/guide",
                            "description": "Other source",
                        },
                    ]
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = BraveSearch(api_key="synthetic-key", http_client=client)
        first = provider.complete(
            "search",
            {"topics": [{"question": "Python hướng dẫn"}]},
            {},
            timeout_s=5,
            web_search=True,
        )
        second = provider.complete(
            "search",
            {"topics": [{"question": "Python hướng dẫn chi tiết"}]},
            {},
            timeout_s=5,
            web_search=True,
        )
    assert len(requests) == 2 and len(provider.events) == 2
    assert first["sources"][0]["url"].startswith("https://docs.python.org/")
    assert first["sources"][1]["url"] == "https://example.org/guide"
    assert second["sources"][0]["description"] == "Actual provider snippet"
    assert provider.events[0]["model_calls"] == 0 and provider.events[0]["http_calls"] == 1


@pytest.mark.parametrize(
    "url",
    [
        "file:///private.xlsx",
        "http://127.0.0.1/x",
        "https://127.0.0.1/x",
        "https://localhost/x",
        "https://[::1]/x",
        "https://10.0.0.1/x",
        "https://secret:password@example.org/x",
    ],
)
def test_search_results_never_enable_private_network_or_file_access(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_workspace_search_passes_all_content_unchanged_including_personal_looking_text(tmp_path):
    from rules.workspace_harness import WorkspaceTools
    from rules.workspace_index import WorkspaceIndex
    from rules.workspaces import WorkspaceStore

    queries = [
        "  email demo@example.invalid CCCD: 123456789012  ",
        "giá điện nhà trọ 2026 2026",
        "Python list comprehension",
    ]
    received = []

    def respond(request):
        received.append(request.url.params["q"])
        return httpx.Response(200, json={"web": {"results": []}})

    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic all-query authorization")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        tools = WorkspaceTools(
            WorkspaceIndex(store, workspace["id"]),
            search=BraveSearch(api_key="synthetic-key", http_client=client),
        )
        for query in queries:
            tools.web_search(query)
    assert received == queries
    assert tools.web_calls == 3
