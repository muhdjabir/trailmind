# Chunking calibration

Implementation list step 2: hand-chunk 2-3 docs manually to calibrate
chunk quality before automating (step 3).

Each `*.md` file here is a **boundary annotation**, not a copy of the
chunked text: it lists, for one source doc in `corpus/da_nang_hoi_an/`,
where a human would cut it into chunks and why. `notes.md` distills
the recurring decisions into rules the step-3 chunker should encode.

Docs picked to cover different structures:
- `hoi_an_wikivoyage.md` — heavily sectioned (H2/H3, `[edit]` markers, lists)
- `da_nang_indietraveller.md` — blog with numbered "things to do" items
- `da_nang_midnightblue.md` — blog, loose narrative prose, few headers
