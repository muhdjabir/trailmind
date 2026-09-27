import pytest
from fastapi.testclient import TestClient

from app.main import app
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
    yield
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
