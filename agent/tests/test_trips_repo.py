import datetime

import pytest

from app.repositories.trips_repo import TripNotFoundError, create_trip, get_trip, list_trips
from app.repositories.vector_store_repo import VectorStoreError, get_connection

pytestmark = pytest.mark.integration

TEST_NAME_PREFIX = "__test_trip__"


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


def test_create_trip_returns_full_row_with_defaults(conn) -> None:
    trip = create_trip(conn, name=f"{TEST_NAME_PREFIX} minimal")

    assert trip.id is not None
    assert trip.name == f"{TEST_NAME_PREFIX} minimal"
    assert trip.destinations == []
    assert trip.status == "draft"
    assert trip.user_id is None


def test_create_trip_with_all_fields(conn) -> None:
    trip = create_trip(
        conn,
        name=f"{TEST_NAME_PREFIX} full",
        user_id="user-1",
        destinations=["da_nang_hoi_an"],
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 8),
        party_size=2,
        budget_planned=1200,
        budget_total=2000,
    )

    assert trip.user_id == "user-1"
    assert trip.destinations == ["da_nang_hoi_an"]
    assert trip.start_date == datetime.date(2026, 11, 1)
    assert trip.party_size == 2
    assert trip.budget_planned == 1200


def test_list_trips_filters_by_user_id(conn) -> None:
    create_trip(conn, name=f"{TEST_NAME_PREFIX} a", user_id="user-a")
    create_trip(conn, name=f"{TEST_NAME_PREFIX} b", user_id="user-b")

    results = list_trips(conn, user_id="user-a")

    assert all(t.user_id == "user-a" for t in results)
    assert any(t.name == f"{TEST_NAME_PREFIX} a" for t in results)
    assert not any(t.name == f"{TEST_NAME_PREFIX} b" for t in results)


def test_list_trips_orders_newest_first(conn) -> None:
    first = create_trip(conn, name=f"{TEST_NAME_PREFIX} first")
    second = create_trip(conn, name=f"{TEST_NAME_PREFIX} second")

    results = list_trips(conn)
    ids = [t.id for t in results]

    assert ids.index(second.id) < ids.index(first.id)


def test_get_trip_returns_matching_trip(conn) -> None:
    created = create_trip(conn, name=f"{TEST_NAME_PREFIX} gettable")

    fetched = get_trip(conn, created.id)

    assert fetched.id == created.id
    assert fetched.name == created.name


def test_get_trip_raises_not_found_for_missing_id(conn) -> None:
    with pytest.raises(TripNotFoundError):
        get_trip(conn, 9_999_999)
