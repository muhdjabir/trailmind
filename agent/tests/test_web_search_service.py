from unittest.mock import Mock, patch

import pytest

from app.services.web_search_service import TavilyError, WebResult, search_web


@patch("app.services.web_search_service.search")
def test_search_web_returns_ranked_results(mock_search: Mock) -> None:
    mock_search.return_value = [
        {"title": "A", "url": "https://a.example", "content": "content a"},
        {"title": "B", "url": "https://b.example", "content": "content b"},
    ]

    results = search_web("weather in paris")

    assert results == [
        WebResult(rank=1, title="A", url="https://a.example", content="content a"),
        WebResult(rank=2, title="B", url="https://b.example", content="content b"),
    ]


@patch("app.services.web_search_service.search")
def test_search_web_propagates_tavily_error(mock_search: Mock) -> None:
    mock_search.side_effect = TavilyError("no key")
    with pytest.raises(TavilyError):
        search_web("weather in paris")
