"""Embed corpus_chunks/<destination>.jsonl into corpus_embeddings/<destination>.jsonl.

Requires `ollama serve` running locally with the embedding model
pulled (default: nomic-embed-text).

Usage:
    python scripts/chunk_corpus.py            # step 3, if not already run
    python scripts/embed_corpus.py [--destination da_nang_hoi_an] [--batch-size 16]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings import DEFAULT_MODEL, EmbeddingError, embed_texts

CHUNKS_ROOT = Path(__file__).resolve().parent.parent / "corpus_chunks"
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "corpus_embeddings"


def embed_file(chunks_path: Path, model: str, batch_size: int) -> list[dict]:
    records = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        vectors = embed_texts([r["text"] for r in batch], model=model)
        for record, vector in zip(batch, vectors):
            record["embedding"] = vector
            record["embedding_model"] = model
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", help="Only embed this destination's chunk file")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    if not CHUNKS_ROOT.exists():
        print(f"error: {CHUNKS_ROOT} does not exist — run scripts/chunk_corpus.py first", file=sys.stderr)
        sys.exit(1)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    chunk_files = (
        [CHUNKS_ROOT / f"{args.destination}.jsonl"]
        if args.destination
        else sorted(CHUNKS_ROOT.glob("*.jsonl"))
    )

    for chunks_path in chunk_files:
        if not chunks_path.exists():
            print(f"[skip] no such file: {chunks_path}", file=sys.stderr)
            continue
        try:
            records = embed_file(chunks_path, args.model, args.batch_size)
        except EmbeddingError as e:
            print(f"[error] {chunks_path.name}: {e}", file=sys.stderr)
            sys.exit(1)

        out_path = OUTPUT_ROOT / chunks_path.name
        with out_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"[ok] embedded {len(records)} chunks -> {out_path.relative_to(OUTPUT_ROOT.parent)}")


if __name__ == "__main__":
    main()
