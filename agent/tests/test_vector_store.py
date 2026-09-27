import pytest

from app.vector_store import VectorStoreError, get_connection, search, upsert_chunks

pytestmark = pytest.mark.integration


def _sample_record(
    destination: str, chunk_id: int, embedding: list[float], city: str | None = None
) -> dict:
    return {
        "chunk_id": chunk_id,
        "section_path": "Test > Section",
        "text": f"Sample chunk text {chunk_id}",
        "word_count": 4,
        "possibly_orphaned": False,
        "metadata": {
            "destination": destination,
            "country": "vietnam" if city else None,
            "city": city,
            "doc_type": "blog",
            "source_url": "https://example.com",
        },
        "source_file": "test-doc.md",
        "embedding": embedding,
        "embedding_model": "test-model",
    }


@pytest.fixture
def conn():
    try:
        connection = get_connection()
    except VectorStoreError as e:
        pytest.skip(f"local postgres not reachable: {e}")
    yield connection
    with connection.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE source_file = 'test-doc.md'")
    connection.commit()
    connection.close()


# Dedicated fake destination so these tests never collide with real
# seeded corpus data (e.g. "da_nang_hoi_an" has real production rows).
TEST_DESTINATION = "test_destination_vector_store"


def test_upsert_then_search_returns_nearest_first(conn) -> None:
    close = [0.0] * 767 + [1.0]
    far = [1.0] + [0.0] * 767
    upsert_chunks(
        conn,
        [
            _sample_record(TEST_DESTINATION, 1, close),
            _sample_record(TEST_DESTINATION, 2, far),
        ],
    )

    results = search(conn, query_embedding=close, destination=TEST_DESTINATION, top_k=2)
    assert results[0]["chunk_id"] == 1
    assert results[0]["distance"] < results[-1]["distance"]


def test_search_respects_destination_filter(conn) -> None:
    vec = [0.5] * 768
    upsert_chunks(
        conn,
        [
            _sample_record(TEST_DESTINATION, 1, vec),
            _sample_record("almaty", 2, vec),
        ],
    )

    results = search(conn, query_embedding=vec, destination=TEST_DESTINATION, top_k=10)
    assert all(r["destination"] == TEST_DESTINATION for r in results)
    assert any(r["source_file"] == "test-doc.md" for r in results)


def test_search_respects_city_filter_within_a_destination(conn) -> None:
    vec = [0.5] * 768
    upsert_chunks(
        conn,
        [
            _sample_record(TEST_DESTINATION, 1, vec, city="hoi_an"),
            _sample_record(TEST_DESTINATION, 2, vec, city="da_nang"),
        ],
    )

    results = search(conn, query_embedding=vec, destination=TEST_DESTINATION, city="hoi_an", top_k=10)
    assert all(r["city"] == "hoi_an" for r in results)
    assert any(r["chunk_id"] == 1 for r in results)
    assert not any(r["chunk_id"] == 2 for r in results)


def test_upsert_is_idempotent_on_conflict(conn) -> None:
    vec = [0.1] * 768
    upsert_chunks(conn, [_sample_record(TEST_DESTINATION, 1, vec)])
    upsert_chunks(conn, [_sample_record(TEST_DESTINATION, 1, vec)])

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM chunks WHERE source_file = 'test-doc.md' AND chunk_id = 1"
        )
        assert cur.fetchone()[0] == 1


def test_get_connection_raises_typed_error_on_bad_url() -> None:
    with pytest.raises(VectorStoreError):
        get_connection("postgresql://nobody:nobody@127.0.0.1:59999/nope")
