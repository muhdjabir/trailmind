from unittest.mock import Mock, patch

import pytest

from app.tools import Snippet, UnknownDestinationError, search_destination_knowledge


@patch("app.tools.retrieve")
def test_unknown_destination_raises_without_calling_retrieve(mock_retrieve: Mock) -> None:
    with pytest.raises(UnknownDestinationError, match="bali"):
        search_destination_knowledge("bali", "best beaches")
    mock_retrieve.assert_not_called()


@patch("app.tools.retrieve")
def test_known_destination_returns_ranked_snippets(mock_retrieve: Mock) -> None:
    mock_retrieve.return_value = [
        {
            "text": "Tailor shops in Hoi An...",
            "source_url": "https://en.wikivoyage.org/wiki/Hoi_An",
            "section_path": "Buy > Shopping > Bespoke clothing",
            "distance": 0.26,
        },
        {
            "text": "Hoi An has a beach too...",
            "source_url": "https://example.com",
            "section_path": "See > Beaches",
            "distance": 0.31,
        },
    ]

    results = search_destination_knowledge("da_nang_hoi_an", "tailor shops", top_k=2)

    mock_retrieve.assert_called_once_with(
        "tailor shops", destination="da_nang_hoi_an", top_k=2, conn=None
    )
    assert results == [
        Snippet(
            rank=1,
            text="Tailor shops in Hoi An...",
            source_url="https://en.wikivoyage.org/wiki/Hoi_An",
            section_path="Buy > Shopping > Bespoke clothing",
            distance=0.26,
        ),
        Snippet(
            rank=2,
            text="Hoi An has a beach too...",
            source_url="https://example.com",
            section_path="See > Beaches",
            distance=0.31,
        ),
    ]


@patch("app.tools.retrieve")
def test_retrieve_errors_propagate_unwrapped(mock_retrieve: Mock) -> None:
    mock_retrieve.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError, match="boom"):
        search_destination_knowledge("bangkok", "street food")
