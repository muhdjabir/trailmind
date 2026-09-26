from app.chunking import chunk_document

DOC_WITH_SMALL_SECTIONS = """---
source_url: https://example.com/x
destination: da_nang_hoi_an
doc_type: wikivoyage
title: Example
fetched_date: 2026-01-01
---

**Example** is a city.

## Understand

[edit]
This is a long paragraph about the city with plenty of words to make
sure it clears the minimum chunk size threshold on its own without
needing to merge with anything else nearby, easily.

### Orientation

[edit]
Small area.

## Get in

[edit]
### By plane

[edit]
Fly in through the international airport, which has domestic and
regional connections and is easily reached by taxi or rideshare from
most parts of the city in well under an hour depending on traffic,
even during the busiest times of day when roads are more congested
than usual and drivers take longer alternate routes to avoid jams.

### By bus

[edit]
Take a bus, it is a long enough paragraph about buses that it should
not be merged into anything else since it clears the minimum word
count threshold on its own comfortably, with several departures each
day from the main terminal and tickets available both online and in
person at the counter for a modest fare.
"""

DOC_WITH_NOISE = """---
destination: bangkok
doc_type: blog
title: Noisy
---

*This post contains affiliate links. Read our disclosure and affiliate policy here.*

…

## Section

[edit]
Real content here, long enough to stand on its own as a chunk without
triggering the small-section merge pass in this test scenario, good.
"""

DOC_WITH_ORPHAN = """---
destination: bangkok
doc_type: blog
title: Orphan test
---

## Working Remotely

Coworking spaces are plentiful and cheap for digital nomads staying
long term, with fast wifi in most cafes around the city center area.

Motorbike rental shops near the mountain pass require a valid license
and a deposit before handing over the scooter for your road trip.
"""


def test_small_sibling_sections_merge_into_previous() -> None:
    chunks = chunk_document(DOC_WITH_SMALL_SECTIONS)
    orientation_chunks = [c for c in chunks if "Orientation" in c.section_path]
    assert len(orientation_chunks) == 1
    merged = orientation_chunks[0]
    assert "Understand" in merged.section_path
    assert merged.word_count > 20  # not just the 2-word Orientation section alone


def test_headers_split_into_separate_chunks() -> None:
    chunks = chunk_document(DOC_WITH_SMALL_SECTIONS)
    paths = [c.section_path for c in chunks]
    assert any(p.endswith("By plane") for p in paths)
    assert any(p.endswith("By bus") for p in paths)


def test_edit_markers_stripped() -> None:
    chunks = chunk_document(DOC_WITH_SMALL_SECTIONS)
    assert not any("[edit]" in c.text for c in chunks)


def test_noise_paragraphs_dropped() -> None:
    chunks = chunk_document(DOC_WITH_NOISE)
    full_text = " ".join(c.text for c in chunks)
    assert "affiliate" not in full_text.lower()
    assert "…" not in full_text


def test_metadata_carried_per_chunk() -> None:
    chunks = chunk_document(DOC_WITH_NOISE)
    assert all(c.metadata["destination"] == "bangkok" for c in chunks)
    assert all(c.metadata["doc_type"] == "blog" for c in chunks)


def test_orphan_paragraph_flagged() -> None:
    chunks = chunk_document(DOC_WITH_ORPHAN)
    assert any(c.possibly_orphaned for c in chunks)


def test_comment_thread_section_dropped() -> None:
    doc = """---
destination: bangkok
doc_type: blog
title: Comments test
---

## What to do

Real travel content about the city, long enough to clear the minimum
chunk size threshold on its own without needing to merge, easily.

## 10 comments

Great article, thanks for sharing your trip! Really helpful tips for
our own upcoming visit, we can't wait to see it for ourselves too.
"""
    chunks = chunk_document(doc)
    assert not any("comment" in c.section_path.lower() for c in chunks)
    assert not any("Great article" in c.text for c in chunks)


def test_intro_not_flagged_as_orphan() -> None:
    doc = """---
destination: bangkok
doc_type: blog
title: Intro test
---

This is just an opening paragraph with no heading above it at all,
long enough to clear the minimum word count needed to be checked by
the orphan-detection heuristic in the first place, comfortably so,
with a few extra words thrown in here just to be entirely certain
that it clears the merge threshold on its own without any help.

## Real Section

More content under a real heading, long enough to clear the minimum
chunk size threshold on its own without needing to merge, certainly,
with a few extra words thrown in here just to be entirely certain
that it clears the merge threshold on its own without any help too.
"""
    chunks = chunk_document(doc)
    intro = next(c for c in chunks if c.section_path == "(intro)")
    assert not intro.possibly_orphaned


def test_headerless_doc_falls_back_to_paragraph_grouping() -> None:
    paragraph = (
        "This is a long paragraph about the destination with plenty of "
        "words describing the local attractions, food, and culture so "
        "that it reliably clears a couple hundred words on its own. "
    ) * 3
    body = "\n\n".join([paragraph] * 6)
    doc = f"""---
destination: bangkok
doc_type: blog
title: Headerless
---

{body}
"""
    chunks = chunk_document(doc)
    assert len(chunks) > 1
    assert all(c.word_count < 300 for c in chunks)
