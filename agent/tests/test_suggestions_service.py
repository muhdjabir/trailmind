import datetime

from app.repositories.trips_repo import Trip
from app.services.suggestions_service import build_suggestions
from app.services.weather_service import WeatherResult


def _trip(**overrides) -> Trip:
    defaults = dict(
        id=1, user_id=None, name="t", destinations=[], start_date=None, end_date=None,
        party_size=None, status="draft", budget_planned=None, budget_total=None,
        created_at=datetime.datetime(2026, 1, 1), updated_at=datetime.datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return Trip(**defaults)


def _weather(total_mm: float, days: int = 4) -> WeatherResult:
    start = datetime.date(2026, 11, 6)
    return WeatherResult("historical_average", start, start + datetime.timedelta(days=days - 1),
                         28.0, 23.0, total_mm, 3)


def test_blank_trip_asks_for_destination() -> None:
    assert build_suggestions(_trip(), None, 0, [], None) == ["Help us pick a destination"]


def test_destination_without_dates_uses_display_name() -> None:
    chips = build_suggestions(_trip(destinations=["da_nang_hoi_an"]), None, 0, [], None)
    assert chips == [
        "When's the best time to visit Da Nang & Hoi An?",
        "Where to eat in Da Nang & Hoi An?",
        "How much should we budget?",
    ]


def test_free_text_destination_kept_as_is() -> None:
    chips = build_suggestions(_trip(destinations=["Paris"], budget_total=900), None, 0, [], None)
    assert "Where to eat in Paris?" in chips


def test_dated_trip_with_nothing_planned_offers_full_plan() -> None:
    chips = build_suggestions(_trip(destinations=["bangkok"]), 4, 0, [1, 2, 3, 4], None)
    assert chips[0] == "Plan the whole trip day by day"


def test_partially_planned_offers_first_open_day() -> None:
    chips = build_suggestions(_trip(destinations=["bangkok"]), 4, 2, [2, 4], None)
    assert chips[0] == "Plan day 2"


def test_rainy_weather_adds_rain_plan() -> None:
    chips = build_suggestions(_trip(destinations=["bangkok"]), 4, 2, [2, 4], _weather(40.0))
    assert chips[:2] == ["Plan day 2", "What can we do if it rains?"]


def test_dry_weather_no_rain_plan() -> None:
    chips = build_suggestions(_trip(destinations=["bangkok"]), 4, 2, [2, 4], _weather(4.0))
    assert "What can we do if it rains?" not in chips


def test_fully_planned_trip_with_budget_asks_what_is_missing() -> None:
    chips = build_suggestions(_trip(destinations=["bangkok"], budget_total=3000), 4, 4, [], None)
    assert chips == ["Where to eat in Bangkok?", "What are we missing?"]


def test_never_more_than_three() -> None:
    chips = build_suggestions(_trip(destinations=["bangkok"]), 4, 2, [2, 4], _weather(40.0))
    assert len(chips) == 3
