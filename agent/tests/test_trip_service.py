from unittest.mock import Mock, patch

import pytest

from app.services.trip_service import InvalidTripDetailsError, set_trip_details


@patch("app.services.trip_service.update_trip_details")
def test_only_given_fields_are_written(mock_update: Mock) -> None:
    conn = Mock()
    set_trip_details(conn, 1, party_size=2, budget_total=2400)
    mock_update.assert_called_once_with(conn, 1, {"party_size": 2, "budget_total": 2400})


@patch("app.services.trip_service.update_trip_details")
def test_known_destinations_normalized_to_slugs_others_kept(mock_update: Mock) -> None:
    set_trip_details(Mock(), 1, destinations=["Da Nang Hoi An", "bangkok", " Paris ", "BANGKOK"])
    fields = mock_update.call_args.args[2]
    assert fields == {"destinations": ["da_nang_hoi_an", "bangkok", "Paris"]}


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"destinations": []},
        {"destinations": "Hoi An"},
        {"destinations": ["Hoi An", "  "]},
        {"party_size": 0},
        {"party_size": "2"},
        {"party_size": True},
        {"budget_total": -5},
        {"budget_planned": "2400"},
    ],
)
@patch("app.services.trip_service.update_trip_details")
def test_invalid_details_rejected_before_db(mock_update: Mock, kwargs: dict) -> None:
    with pytest.raises(InvalidTripDetailsError):
        set_trip_details(Mock(), 1, **kwargs)
    mock_update.assert_not_called()
