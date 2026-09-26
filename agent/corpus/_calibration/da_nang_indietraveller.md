# Chunk boundaries — da-nang-travel-guide-with-top-things-to-do-in-2026.md

Source: `corpus/da_nang_hoi_an/da-nang-travel-guide-with-top-things-to-do-in-2026.md`

| # | Section path | Lines | Note |
|---|---|---|---|
| 1 | Intro | 9–17 | Personal-narrative framing, not much retrievable fact — low priority chunk but kept for context/tone queries. |
| 2 | Is it Worth Staying? Da Nang vs. Hoi An | 19–41 | One chunk: it's a single comparison argument, splitting mid-argument would strand the conclusion from its reasoning. |
| 3 | Where to Stay (overview) | 43–56 | General framing before the per-area breakdown. |
| 4 | Where to Stay > An Thuong / My An Beach | 57–61 | |
| 5 | Where to Stay > My Khe Beach | 63–69 | |
| 6 | Where to Stay > City Center/Downtown | 71–77 | |
| 7 | Where to Stay > Big Beach Resorts | 79–83 | |
| 8 | Where to Stay > Son Tra Peninsula | 85–89 | |
| 9–23 | Best Things to Do > items 1–15 | 93–241 | **One chunk per numbered item** (My Khe Beach, Surf Lessons, Hoi An, Hai Van Pass, Hue, Marble Mountain, Lady Buddha, Son Tra Peninsula, Dragon Bridge, My Son, food tour, Cham Islands, Massage, Ba Na Hills, Cafes/Bars). Each item's own H3 + paragraphs is already a complete, self-contained semantic unit — no merging or splitting needed. |
| 24 | Working Remotely | 243–253 | |
| 25 | Orphaned motorbike-rental aside | 255–259 | **Split out, not left attached to "Working Remotely."** Content is actually about Hai Van Pass licensing/rental shops (topically belongs near item 4, "Hai Van Pass," lines 121–129) but sits physically under the wrong header in the source — an editing/insertion artifact. Chunking it separately avoids polluting the "Working Remotely" embedding with unrelated motorbike-rental content. |

23 chunks. Confirms: numbered "best things to do" blog sections are
the easiest case — the author has already done the semantic chunking
for you via H3 headings. The one non-obvious call is #25: a chunker
that blindly follows header nesting will glue that paragraph to
"Working Remotely," where it doesn't semantically belong.
