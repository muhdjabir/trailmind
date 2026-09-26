# Chunk boundaries — practical-da-nang-travel-guide-2025-the-midnight-blue-elepha.md

Source: `corpus/da_nang_hoi_an/practical-da-nang-travel-guide-2025-the-midnight-blue-elepha.md`

| # | Section path | Lines | Note |
|---|---|---|---|
| 0 | Affiliate disclosure | 9 | **Drop, don't chunk.** Boilerplate, no travel content, would only add noise to embeddings. |
| — | Stray `…` line | 11 | **Drop.** Extraction artifact (likely a stripped newsletter signup block), not content. |
| 1 | Intro + quick tips box | 13–32 | Merged: opening narrative (why the author stopped over) plus the quick-tips box (hotel pick, activity list) — the box only makes sense with the intro's framing that this is a short-stopover guide. |
| 2 | Da Nang attractions | 34–40 | |
| 3 | Best Da Nang food (intro + bun cha ca) | 42–54 | One chunk: the food-tour tip line (54) is a direct aside on the same story, not a separate topic. |
| 4 | Secret Cocktail Experience | 56–64 | |
| 5 | How to get to Da Nang & get around | 68–76 | |
| 6 | SIM card & wifi | 78–90 | |
| 7 | Money matters | 92–98 | |
| 8 | Where to stay | 100–110 | |

8 real content chunks (+2 dropped non-content lines) out of ~250
lines. Confirms the opposite lesson from the Wikivoyage doc: a loose
blog with only H2/H3 headers every 10-20 lines needs topic-shift
detection, not header-splitting, since headers alone under-segment
(e.g. "Best Da Nang food" already covers two sub-stories) while also
occasionally over-segmenting nothing — here headers happened to align
with good boundaries once the intro was merged forward. The bigger
risk in this doc type is **not** noticing non-content boilerplate
(disclosure, stray extraction artifacts) and chunking it as if it
were real corpus text.
