from unittest.mock import Mock, patch

from app.retrieval import retrieve


@patch("app.retrieval.get_connection")
@patch("app.retrieval.search")
@patch("app.retrieval.embed_texts")
def test_retrieve_embeds_query_and_searches(
    mock_embed: Mock, mock_search: Mock, mock_get_connection: Mock
) -> None:
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_search.return_value = [{"text": "chunk text", "source_url": "https://example.com"}]
    mock_conn = Mock()
    mock_get_connection.return_value = mock_conn

    result = retrieve("things to do in Hoi An", destination="da_nang_hoi_an", top_k=3)

    mock_embed.assert_called_once_with(["things to do in Hoi An"])
    mock_search.assert_called_once_with(
        mock_conn, [0.1, 0.2, 0.3], destination="da_nang_hoi_an", city=None, top_k=3
    )
    assert result == [{"text": "chunk text", "source_url": "https://example.com"}]


@patch("app.retrieval.get_connection")
@patch("app.retrieval.search")
@patch("app.retrieval.embed_texts")
def test_retrieve_passes_city_through_to_search(
    mock_embed: Mock, mock_search: Mock, mock_get_connection: Mock
) -> None:
    mock_embed.return_value = [[0.1, 0.2, 0.3]]
    mock_conn = Mock()
    mock_get_connection.return_value = mock_conn

    retrieve("tailors in Hoi An", destination="da_nang_hoi_an", city="hoi_an", top_k=3)

    mock_search.assert_called_once_with(
        mock_conn, [0.1, 0.2, 0.3], destination="da_nang_hoi_an", city="hoi_an", top_k=3
    )


@patch("app.retrieval.get_connection")
@patch("app.retrieval.search")
@patch("app.retrieval.embed_texts")
def test_retrieve_closes_connection_it_opened(
    mock_embed: Mock, mock_search: Mock, mock_get_connection: Mock
) -> None:
    mock_embed.return_value = [[0.1]]
    mock_conn = Mock()
    mock_get_connection.return_value = mock_conn

    retrieve("query")

    mock_conn.close.assert_called_once()


@patch("app.retrieval.search")
@patch("app.retrieval.embed_texts")
def test_retrieve_does_not_close_a_passed_in_connection(
    mock_embed: Mock, mock_search: Mock
) -> None:
    mock_embed.return_value = [[0.1]]
    mock_conn = Mock()

    retrieve("query", conn=mock_conn)

    mock_conn.close.assert_not_called()
