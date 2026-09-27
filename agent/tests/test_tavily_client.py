from unittest.mock import Mock, patch

import pytest
import requests

from app.tavily_client import TavilyError, search

SAMPLE_RESULTS = [
    {"title": "Paris weather guide", "url": "https://example.com/paris", "content": "Mild and rainy."},
]


@patch("app.tavily_client.requests.post")
def test_search_returns_normalized_results(mock_post: Mock) -> None:
    mock_post.return_value = Mock(status_code=200, json=lambda: {"results": SAMPLE_RESULTS})
    result = search("weather in paris", api_key="test-key")
    assert result == [
        {"title": "Paris weather guide", "url": "https://example.com/paris", "content": "Mild and rainy."}
    ]


def test_missing_api_key_raises_tavily_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(TavilyError, match="TAVILY_API_KEY"):
        search("weather in paris", api_key=None)


@patch("app.tavily_client.requests.post")
def test_connection_error_raises_tavily_error(mock_post: Mock) -> None:
    mock_post.side_effect = requests.ConnectionError("refused")
    with pytest.raises(TavilyError, match="could not reach"):
        search("weather in paris", api_key="test-key")


@patch("app.tavily_client.requests.post")
def test_non_200_raises_tavily_error(mock_post: Mock) -> None:
    mock_post.return_value = Mock(status_code=401, text="unauthorized")
    with pytest.raises(TavilyError, match="401"):
        search("weather in paris", api_key="bad-key")


@patch("app.tavily_client.requests.post")
def test_missing_results_key_raises_tavily_error(mock_post: Mock) -> None:
    mock_post.return_value = Mock(status_code=200, json=lambda: {"unexpected": "shape"})
    with pytest.raises(TavilyError, match="unexpected"):
        search("weather in paris", api_key="test-key")
