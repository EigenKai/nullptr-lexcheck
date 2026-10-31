"""Brave web-search observations; no government-domain restriction or call quota."""

import html
import ipaddress
import os
import re
import uuid
from urllib.parse import urldefrag, urlparse

import httpx


def validate_public_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not host
    ):
        raise ValueError("Search source must be a public HTTPS URL.")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "%" in host:
        raise ValueError("Private/local search source is not allowed.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise ValueError("Private/local search source is not allowed.") from None
    else:
        if not address.is_global:
            raise ValueError("Private/local search source is not allowed.")
    return urldefrag(url)[0]


def _text(value, limit):
    return html.unescape(re.sub(r"<[^>]*>", "", str(value or "")))[:limit]


class BraveSearch:
    def __init__(self, *, api_key=None, http_client=None):
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        if not self.api_key:
            raise RuntimeError("Configure BRAVE_SEARCH_API_KEY before web search.")
        self.http_client, self.events = http_client, []

    def complete(self, stage, payload, schema, *, timeout_s, web_search=False):
        if stage != "search" or not web_search:
            raise ValueError("Brave adapter supports web search only.")
        query = payload["topics"][0]["question"]
        if not isinstance(query, str) or not query.strip() or len(query) > 600:
            raise ValueError("Invalid search query.")
        event = {
            "provider": "brave",
            "request_id": uuid.uuid4().hex,
            "cached": False,
            "model_calls": 0,
            "http_calls": 1,
        }
        self.events.append(event)
        client = self.http_client or httpx.Client(follow_redirects=False)
        try:
            response = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
                params={"q": query, "count": 20, "search_lang": "vi", "extra_snippets": "true"},
                timeout=max(1, timeout_s),
            )
            event["http_status"] = response.status_code
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Never include provider response bodies, headers or credentials in errors.
            raise RuntimeError("Brave Search unavailable; " + type(exc).__name__) from None
        finally:
            if self.http_client is None:
                client.close()
        sources, remaining = [], 30000
        for item in data.get("web", {}).get("results", []):
            try:
                url = validate_public_url(item.get("url", ""))
            except ValueError:
                continue
            if remaining <= 0:
                break
            description = _text(item.get("description"), min(2000, remaining))
            remaining -= len(description)
            snippets = []
            for value in item.get("extra_snippets", [])[:2]:
                snippet = _text(value, min(1000, max(0, remaining)))
                snippets.append(snippet)
                remaining -= len(snippet)
            sources.append(
                {
                    "url": url,
                    "title": _text(item.get("title"), 500),
                    "description": description,
                    "extra_snippets": snippets,
                    "verification_status": "search_observation_unverified",
                    "retrieval_status": "search_observation_only",
                }
            )
        event["results"] = len(sources)
        return {
            "provider": "brave",
            "sources": sources,
            "more_results_available": bool(data.get("query", {}).get("more_results_available")),
            "note": "Actual Brave Search snippets and links. Prefer original/official sources when useful, but other public sources are allowed. Snippets are search observations, not a claim that full original pages were read or legally verified.",
        }
