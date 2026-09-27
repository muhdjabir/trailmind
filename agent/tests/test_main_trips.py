import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.chat_history_repo import append_message
from app.repositories.vector_store_repo import VectorStoreError, get_connection

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
