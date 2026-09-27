import pytest

from app.destinations import DESTINATION_COORDS, UnknownCityError, destination_coords


def test_destination_coords_returns_default_for_known_destination() -> None:
    assert destination_coords("bangkok") == DESTINATION_COORDS["bangkok"]


def test_destination_coords_returns_city_specific_coords() -> None:
    hoi_an = destination_coords("da_nang_hoi_an", city="hoi_an")
    da_nang = destination_coords("da_nang_hoi_an", city="da_nang")
    assert hoi_an != da_nang


def test_destination_coords_raises_for_unknown_city_within_multi_city_destination() -> None:
    with pytest.raises(UnknownCityError, match="quy_nhon"):
        destination_coords("da_nang_hoi_an", city="quy_nhon")


def test_destination_coords_ignores_city_on_single_city_destination() -> None:
    # A single-city destination has no per-city breakdown to validate
    # against, so a redundant/wrong `city` (e.g. an LLM echoing the
    # destination name) falls back to the destination default rather
    # than erroring - see destination_coords' docstring.
    assert destination_coords("bangkok", city="bangkok") == DESTINATION_COORDS["bangkok"]
    assert destination_coords("bangkok", city="anything") == DESTINATION_COORDS["bangkok"]
