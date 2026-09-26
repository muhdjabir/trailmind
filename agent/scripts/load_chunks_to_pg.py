"""Load corpus_embeddings/<destination>.jsonl into the pgvector `chunks` table.

Requires `docker compose up -d` running (see docker-compose.yml).

Usage:
    python scripts/load_chunks_to_pg.py [--destination da_nang_hoi_an]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.vector_store import VectorStoreError, get_connection, upsert_chunks

EMBEDDINGS_ROOT = Path(__file__).resolve().parent.parent / "corpus_embeddings"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", help="Only load this destination's embeddings file")
    args = parser.parse_args()

    if not EMBEDDINGS_ROOT.exists():
        print(f"error: {EMBEDDINGS_ROOT} does not exist — run scripts/embed_corpus.py first", file=sys.stderr)
        sys.exit(1)

    files = (
        [EMBEDDINGS_ROOT / f"{args.destination}.jsonl"]
        if args.destination
        else sorted(EMBEDDINGS_ROOT.glob("*.jsonl"))
    )

    try:
        conn = get_connection()
    except VectorStoreError as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)

    with conn:
        for path in files:
            if not path.exists():
                print(f"[skip] no such file: {path}", file=sys.stderr)
                continue
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            n = upsert_chunks(conn, records)
            print(f"[ok] upserted {n} chunks from {path.name}")


if __name__ == "__main__":
    main()
