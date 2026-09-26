"""Chunk every doc in corpus/<destination>/*.md into corpus_chunks/<destination>.jsonl.

Usage:
    python scripts/chunk_corpus.py [--destination da_nang_hoi_an]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chunking import chunk_document

CORPUS_ROOT = Path(__file__).resolve().parent.parent / "corpus"
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "corpus_chunks"


def chunk_destination(destination_dir: Path) -> list[dict]:
    records: list[dict] = []
    for doc_path in sorted(destination_dir.glob("*.md")):
        raw = doc_path.read_text(encoding="utf-8")
        chunks = chunk_document(raw)
        for chunk in chunks:
            record = dataclasses.asdict(chunk)
            record["source_file"] = doc_path.name
            records.append(record)
        n_flagged = sum(c.possibly_orphaned for c in chunks)
        print(f"[ok] {doc_path.name}: {len(chunks)} chunks ({n_flagged} flagged for review)")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", help="Only chunk this destination subdirectory")
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    destination_dirs = (
        [CORPUS_ROOT / args.destination]
        if args.destination
        else [d for d in CORPUS_ROOT.iterdir() if d.is_dir() and not d.name.startswith("_")]
    )

    for destination_dir in destination_dirs:
        if not destination_dir.is_dir():
            print(f"[skip] no such destination directory: {destination_dir}", file=sys.stderr)
            continue
        records = chunk_destination(destination_dir)
        out_path = OUTPUT_ROOT / f"{destination_dir.name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        print(f"[ok] wrote {len(records)} chunks -> {out_path.relative_to(OUTPUT_ROOT.parent)}")


if __name__ == "__main__":
    main()
