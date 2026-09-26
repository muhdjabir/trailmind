# corpus

Raw source documents for the RAG knowledge base, one subdirectory per
destination (`da_nang_hoi_an/`, `bangkok/`, `almaty/`, `tokyo_fuji_hiroshima/`).

Populate with:

```
python scripts/fetch_corpus.py <url> [<url> ...] --destination da_nang_hoi_an --doc-type blog
```

Each file is markdown with a YAML frontmatter block (`source_url`,
`destination`, `doc_type`, `title`, `fetched_date`) followed by the
cleaned page text. This is the input to the chunking step, not the
chunked/embedded output.

## Chunking

```
python scripts/chunk_corpus.py [--destination da_nang_hoi_an]
```

Splits each doc into semantic-unit chunks per the rules calibrated in
`_calibration/notes.md`, and writes `corpus_chunks/<destination>.jsonl`
(gitignored — regenerate anytime from the committed corpus).
