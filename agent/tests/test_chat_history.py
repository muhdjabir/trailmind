import pytest

from app.chat_history import append_message, list_messages
from app.trips import create_trip
from app.vector_store import VectorStoreError, get_connection

pytestmark = pytest.mark.integration

TEST_NAME_PREFIX = "__test_trip_chat_history__"


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


def test_append_then_list_returns_messages_in_order(conn, trip_id) -> None:
    append_message(conn, trip_id, "user", "best time to visit?")
    append_message(conn, trip_id, "assistant", "November to March.")

    messages = list_messages(conn, trip_id)

    assert [m.role for m in messages] == ["user", "assistant"]
    assert [m.content for m in messages] == ["best time to visit?", "November to March."]


def test_list_messages_scoped_to_trip(conn, trip_id) -> None:
    other_trip_id = create_trip(conn, name=f"{TEST_NAME_PREFIX} other").id
    append_message(conn, trip_id, "user", "for trip A")
    append_message(conn, other_trip_id, "user", "for trip B")

    messages = list_messages(conn, trip_id)

    assert [m.content for m in messages] == ["for trip A"]


def test_list_messages_empty_for_new_trip(conn, trip_id) -> None:
    assert list_messages(conn, trip_id) == []


def test_messages_deleted_when_trip_deleted(conn, trip_id) -> None:
    append_message(conn, trip_id, "user", "hello")

    with conn.cursor() as cur:
        cur.execute("DELETE FROM trips WHERE id = %s", (trip_id,))
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM chat_messages WHERE trip_id = %s", (trip_id,))
        assert cur.fetchone()[0] == 0
