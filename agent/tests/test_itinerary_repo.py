import pytest

from app.repositories.itinerary_repo import delete_day, delete_days_after, list_days, upsert_day
from app.repositories.trips_repo import create_trip
from app.repositories.vector_store_repo import VectorStoreError, get_connection

pytestmark = pytest.mark.integration

TEST_NAME_PREFIX = "__test_trip_itinerary__"


@pytest.fixture
def conn():
    try:
        connection = get_connection()
    except VectorStoreError as e:
        pytest.skip(f"local postgres not reachable: {e}")
    yield connection
    with connection.cursor() as cur:
        cur.execute("DELETE FROM trips WHERE name LIKE %s", (f"{TEST_NAME_PREFIX}%",))
    connection.commit()
    connection.close()


@pytest.fixture
def trip_id(conn):
    return create_trip(conn, name=f"{TEST_NAME_PREFIX} main").id


def test_upsert_then_list_returns_days_in_order(conn, trip_id) -> None:
    upsert_day(conn, trip_id, 2, {"title": "Day two", "items": ["b"]})
    upsert_day(conn, trip_id, 1, {"title": "Day one", "items": ["a"]})

    days = list_days(conn, trip_id)

    assert [d.day_number for d in days] == [1, 2]
    assert days[0].plan == {"title": "Day one", "items": ["a"]}


def test_upsert_same_day_replaces_plan(conn, trip_id) -> None:
    first = upsert_day(conn, trip_id, 1, {"title": "Old", "items": ["x"]})
    second = upsert_day(conn, trip_id, 1, {"title": "New", "items": ["y", "z"]})

    days = list_days(conn, trip_id)

    assert len(days) == 1
    assert days[0].plan == {"title": "New", "items": ["y", "z"]}
    assert second.id == first.id
    assert second.updated_at >= first.updated_at


def test_list_days_scoped_to_trip(conn, trip_id) -> None:
    other_trip_id = create_trip(conn, name=f"{TEST_NAME_PREFIX} other").id
    upsert_day(conn, trip_id, 1, {"title": "Mine", "items": []})
    upsert_day(conn, other_trip_id, 1, {"title": "Theirs", "items": []})

    assert [d.plan["title"] for d in list_days(conn, trip_id)] == ["Mine"]


def test_list_days_empty_for_new_trip(conn, trip_id) -> None:
    assert list_days(conn, trip_id) == []


def test_delete_day_removes_only_that_day(conn, trip_id) -> None:
    upsert_day(conn, trip_id, 1, {"title": "One", "items": []})
    upsert_day(conn, trip_id, 2, {"title": "Two", "items": []})
    upsert_day(conn, trip_id, 3, {"title": "Three", "items": []})

    assert delete_day(conn, trip_id, 2) is True
    assert [d.day_number for d in list_days(conn, trip_id)] == [1, 3]


def test_delete_day_returns_false_when_nothing_saved(conn, trip_id) -> None:
    assert delete_day(conn, trip_id, 1) is False


def test_delete_days_after_removes_later_days_only(conn, trip_id) -> None:
    for n in (1, 3, 4, 6):
        upsert_day(conn, trip_id, n, {"title": str(n), "items": []})

    assert delete_days_after(conn, trip_id, 3) == [4, 6]
    assert [d.day_number for d in list_days(conn, trip_id)] == [1, 3]
