import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.chat_history_repo import append_message
from app.repositories.itinerary_repo import upsert_day
from app.repositories.vector_store_repo import VectorStoreError, get_connection
from app.services.weather_service import WeatherResult

pytestmark = pytest.mark.integration

client = TestClient(app)

TEST_NAME_PREFIX = "__test_trip_api__"


@pytest.fixture(autouse=True)
def _cleanup():
    try:
        conn = get_connection()
    except VectorStoreError as e:
        pytest.skip(f"local postgres not reachable: {e}")
    yield conn
    with conn.cursor() as cur:
        cur.execute("DELETE FROM trips WHERE name LIKE %s", (f"{TEST_NAME_PREFIX}%",))
    conn.commit()
    conn.close()


def test_create_then_get_trip() -> None:
    create_response = client.post(
        "/trips",
        json={"name": f"{TEST_NAME_PREFIX} create", "destinations": ["bangkok"]},
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == f"{TEST_NAME_PREFIX} create"
    assert created["destinations"] == ["bangkok"]
    assert created["status"] == "draft"

    get_response = client.get(f"/trips/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_get_unknown_trip_returns_404() -> None:
    response = client.get("/trips/9999999")
    assert response.status_code == 404


def test_list_trips_includes_created_trip() -> None:
    created = client.post("/trips", json={"name": f"{TEST_NAME_PREFIX} listed"}).json()

    response = client.get("/trips")

    assert response.status_code == 200
    assert any(t["id"] == created["id"] for t in response.json())


def test_list_trip_messages_returns_persisted_history(_cleanup) -> None:
    created = client.post("/trips", json={"name": f"{TEST_NAME_PREFIX} history"}).json()
    append_message(_cleanup, created["id"], "user", "earlier question")
    append_message(_cleanup, created["id"], "assistant", "earlier answer")

    response = client.get(f"/trips/{created['id']}/messages")

    assert response.status_code == 200
    body = response.json()
    assert [m["role"] for m in body] == ["user", "assistant"]
    assert [m["content"] for m in body] == ["earlier question", "earlier answer"]


def test_list_trip_messages_empty_for_trip_with_no_history() -> None:
    created = client.post("/trips", json={"name": f"{TEST_NAME_PREFIX} no history"}).json()

    response = client.get(f"/trips/{created['id']}/messages")

    assert response.status_code == 200
    assert response.json() == []


def test_list_trip_messages_returns_404_for_unknown_trip() -> None:
    response = client.get("/trips/9999999/messages")
    assert response.status_code == 404


def test_itinerary_returns_saved_days_with_derived_dates(_cleanup) -> None:
    created = client.post(
        "/trips",
        json={"name": f"{TEST_NAME_PREFIX} itinerary", "start_date": "2026-10-12",
              "end_date": "2026-10-17"},
    ).json()
    upsert_day(_cleanup, created["id"], 4, {"title": "Train to Porto", "items": ["Alfa Pendular 10:39"]})
    upsert_day(_cleanup, created["id"], 1, {"title": "Arrive Lisbon", "items": []})

    response = client.get(f"/trips/{created['id']}/itinerary")

    assert response.status_code == 200
    body = response.json()
    assert [d["day_number"] for d in body] == [1, 4]
    assert body[1]["date"] == "2026-10-15"
    assert body[1]["title"] == "Train to Porto"
    assert body[1]["items"] == ["Alfa Pendular 10:39"]


def test_itinerary_date_null_when_trip_dates_open(_cleanup) -> None:
    created = client.post("/trips", json={"name": f"{TEST_NAME_PREFIX} open dates"}).json()
    upsert_day(_cleanup, created["id"], 1, {"title": "Somewhere", "items": []})

    body = client.get(f"/trips/{created['id']}/itinerary").json()

    assert body[0]["date"] is None


def test_itinerary_returns_404_for_unknown_trip() -> None:
    assert client.get("/trips/9999999/itinerary").status_code == 404


def test_stats_for_dated_trip_with_days(_cleanup) -> None:
    created = client.post(
        "/trips",
        json={"name": f"{TEST_NAME_PREFIX} stats", "destinations": ["da_nang_hoi_an"],
              "start_date": "2026-11-06", "end_date": "2026-11-09", "budget_total": 2000},
    ).json()
    upsert_day(_cleanup, created["id"], 1, {"title": "Arrive", "items": []})
    weather = WeatherResult("historical_average", datetime.date(2026, 11, 6),
                            datetime.date(2026, 11, 9), 27.04, 22.0, 60.0, 3)

    with patch("app.services.trip_stats_service.get_weather", return_value=weather):
        response = client.get(f"/trips/{created['id']}/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["trip_days"] == 4
    assert body["days_planned"] == 1
    assert body["open_days"] == [2, 3, 4]
    assert body["budget_total"] == 2000
    assert body["weather"] == {
        "destination": "da_nang_hoi_an",
        "source": "historical_average",
        "avg_high_c": 27.0,
        "avg_low_c": 22.0,
        "total_precipitation_mm": 60.0,
    }
    assert body["weather_error"] is None


def test_stats_returns_404_for_unknown_trip() -> None:
    assert client.get("/trips/9999999/stats").status_code == 404
