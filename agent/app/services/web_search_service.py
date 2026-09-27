"""search_web tool: fallback for destinations the curated knowledge base
doesn't cover (see CLAUDE.md "Tools" and the "Considered for later" note
in docs/implementation_list.md this implements).

Deliberately separate from search_destination_knowledge, not blended
into it - curated corpus answers and live-web answers stay clearly
distinguishable, per that same design note. chat_service's system
prompt is what tells the LLM to flag results from this tool as such.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.tavily_client import TavilyError, search

__all__ = ["TavilyError", "WebResult", "search_web"]


@dataclass
class WebResult:
    rank: int
    title: str
    url: str
    content: str


def search_web(query: str, max_results: int = 5) -> list[WebResult]:
    """Ranked web results for `query`. Raises TavilyError - never a silent failure."""
    results = search(query, max_results=max_results)
    return [
        WebResult(rank=i + 1, title=r["title"], url=r["url"], content=r["content"])
        for i, r in enumerate(results)
    ]
