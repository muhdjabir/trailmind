"""Web search via Tavily (used only as a fallback for destinations the
curated knowledge base doesn't cover - see app.services.web_search_service).

Requires TAVILY_API_KEY (free tier at tavily.com). Unlike Ollama/
Open-Meteo, this is a paid-beyond-free-tier third-party API, so it's
opt-in: a missing key is a typed error, not a crash at import time.
"""

from __future__ import annotations

import os

import requests

SEARCH_URL = "https://api.tavily.com/search"
DEFAULT_MAX_RESULTS = 5


class TavilyError(Exception):
    """Typed error for Tavily failures (missing key, unreachable, bad response, etc.)."""


def search(
    query: str,
    api_key: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
    timeout: float = 15.0,
) -> list[dict]:
    """Ranked [{title, url, content}] web results for `query`."""
    key = api_key if api_key is not None else os.environ.get("TAVILY_API_KEY")
    if not key:
        raise TavilyError(
            "TAVILY_API_KEY is not set - web search is unavailable without it"
        )

    try:
        response = requests.post(
            SEARCH_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"query": query, "max_results": max_results, "search_depth": "basic"},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise TavilyError(f"could not reach Tavily: {e}") from e

    if response.status_code != 200:
        raise TavilyError(f"Tavily returned {response.status_code}: {response.text}")

    data = response.json()
    results = data.get("results")
    if results is None:
        raise TavilyError(f"unexpected Tavily response shape: {data}")

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in results
    ]
