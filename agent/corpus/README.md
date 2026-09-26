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
