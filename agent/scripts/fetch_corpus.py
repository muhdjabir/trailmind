"""Fetch web pages and save them as clean markdown for the RAG corpus.

Usage:
    python scripts/fetch_corpus.py <url> [<url> ...] \
        --destination da_nang_hoi_an --doc-type blog

Each URL is fetched, stripped of boilerplate (nav/ads/sidebars) via
trafilatura, and written to corpus/<destination>/<slug>.md with a
YAML frontmatter block recording source_url, destination, doc_type,
and fetched_date.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

import trafilatura
import yaml

CORPUS_ROOT = Path(__file__).resolve().parent.parent / "corpus"

KNOWN_DESTINATIONS = {
    "da_nang_hoi_an",
    "bangkok",
    "almaty",
    "tokyo_fuji_hiroshima",
}


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len].rstrip("-") or "untitled"


def unique_path(directory: Path, slug: str) -> Path:
    candidate = directory / f"{slug}.md"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{slug}-{counter}.md"
        counter += 1
    return candidate


def fetch_one(url: str, destination: str, doc_type: str) -> Path | None:
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        print(f"[skip] could not fetch: {url}", file=sys.stderr)
        return None

    metadata = trafilatura.extract_metadata(downloaded)
    title = (metadata.title if metadata and metadata.title else url)

    body = trafilatura.extract(
        downloaded,
        output_format="markdown",
        with_metadata=False,
        include_links=False,
        include_images=False,
    )
    if not body:
        print(f"[skip] no extractable content: {url}", file=sys.stderr)
        return None

    dest_dir = CORPUS_ROOT / destination
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = unique_path(dest_dir, slugify(title))

    frontmatter_data = {
        "source_url": url,
        "destination": destination,
        "doc_type": doc_type,
        "title": title,
        "fetched_date": datetime.date.today().isoformat(),
    }
    frontmatter = "---\n" + yaml.safe_dump(frontmatter_data, allow_unicode=True, sort_keys=False) + "---\n\n"
    out_path.write_text(frontmatter + body, encoding="utf-8")
    print(f"[ok] {url} -> {out_path.relative_to(CORPUS_ROOT.parent)}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+", help="One or more page URLs to fetch")
    parser.add_argument(
        "--destination",
        required=True,
        help=f"One of: {', '.join(sorted(KNOWN_DESTINATIONS))}",
    )
    parser.add_argument(
        "--doc-type",
        default="blog",
        help="e.g. blog, forum, tourism_board, wikivoyage (default: blog)",
    )
    args = parser.parse_args()

    if args.destination not in KNOWN_DESTINATIONS:
        print(
            f"warning: '{args.destination}' is not in the known destination "
            f"list ({', '.join(sorted(KNOWN_DESTINATIONS))}) — continuing anyway",
            file=sys.stderr,
        )

    for url in args.urls:
        fetch_one(url, args.destination, args.doc_type)


if __name__ == "__main__":
    main()
