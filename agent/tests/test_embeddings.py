from unittest.mock import Mock, patch

import pytest
import requests

from app.embeddings import EmbeddingError, embed_texts


def test_empty_input_returns_empty_list() -> None:
    assert embed_texts([]) == []


@patch("app.embeddings.requests.post")
def test_embed_texts_returns_vectors(mock_post: Mock) -> None:
    mock_post.return_value = Mock(
        status_code=200,
        json=lambda: {"embeddings": [[0.1, 0.2], [0.3, 0.4]]},
    )
    result = embed_texts(["a", "b"])
    assert result == [[0.1, 0.2], [0.3, 0.4]]
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["input"] == ["a", "b"]


@patch("app.embeddings.requests.post")
def test_connection_error_raises_embedding_error(mock_post: Mock) -> None:
    mock_post.side_effect = requests.ConnectionError("refused")
    with pytest.raises(EmbeddingError, match="ollama serve"):
        embed_texts(["a"])


@patch("app.embeddings.requests.post")
def test_non_200_raises_embedding_error(mock_post: Mock) -> None:
    mock_post.return_value = Mock(status_code=500, text="boom")
    with pytest.raises(EmbeddingError, match="500"):
        embed_texts(["a"])


@patch("app.embeddings.requests.post")
def test_mismatched_response_shape_raises_embedding_error(mock_post: Mock) -> None:
    mock_post.return_value = Mock(status_code=200, json=lambda: {"embeddings": [[0.1]]})
    with pytest.raises(EmbeddingError):
        embed_texts(["a", "b"])
