"""Chunk corpus markdown docs into semantic-unit-first chunks.

Rules encoded here come from the hand-chunking calibration in
corpus/_calibration/notes.md:

1. Split on markdown headers (any level) first.
2. Merge a section into the previous one in reading order if it's
   too small to carry standalone meaning on its own.
3. Strip non-content noise (Wikivoyage `[edit]` markers, stray
   ellipsis artifacts, affiliate-disclosure boilerplate) before
   chunking rather than emitting it as a chunk.
4. Flag (not auto-fix) chunks whose text shares little vocabulary
   with their own heading path — a cheap signal for orphaned content
   sitting under the wrong header.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
MIN_CHUNK_WORDS = 40
FALLBACK_TARGET_WORDS = 200
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "to", "for",
    "with", "by", "at", "is", "are", "your", "you", "it", "this",
    "that", "from", "as", "be", "get", "go", "do",
}

NOISE_LINE_PATTERNS = [
    re.compile(r"^\[edit\]$"),
    re.compile(r"^\.{3}$"),
    re.compile(r"^…$"),
]
NOISE_HEADING_PATTERNS = [
    re.compile(r"^\d+\s+comments?$", re.IGNORECASE),
    re.compile(r"^leave a (reply|comment)$", re.IGNORECASE),
]
NOISE_PARAGRAPH_PATTERNS = [
    re.compile(r"affiliate link", re.IGNORECASE),
    re.compile(r"disclosure and affiliate policy", re.IGNORECASE),
]

# Travel-guide headers whose prose rarely repeats the header word
# itself (e.g. a "Sleep" section talks about hotels, not sleeping).
# Expands the orphan-detection keyword set so literal-overlap doesn't
# flag every well-placed section under one of these common headers.
HEADING_SYNONYMS: dict[str, set[str]] = {
    "sleep": {"hotel", "hostel", "resort", "guesthouse", "room", "stay", "accommodation", "villa"},
    "eat": {"restaurant", "food", "dish", "cuisine", "menu", "meal", "noodle", "rice"},
    "drink": {"bar", "pub", "cocktail", "beer", "cafe", "coffee"},
    "buy": {"shop", "market", "store", "price", "dong", "souvenir"},
    "plane": {"airport", "flight", "fly", "airline", "terminal"},
    "train": {"railway", "station", "rail"},
    "bus": {"coach", "shuttle", "minivan", "terminal"},
    "taxi": {"grab", "cab", "driver", "fare"},
    "do": {"tour", "activity", "experience", "visit", "explore"},
    "see": {"temple", "museum", "landmark", "attraction", "sight"},
}


@dataclass
class Section:
    heading_path: list[str]
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass
class Chunk:
    chunk_id: int
    section_path: str
    text: str
    word_count: int
    possibly_orphaned: bool
    metadata: dict


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---\n"):
        return {}, raw
    end = raw.find("\n---\n", 4)
    if end == -1:
        return {}, raw
    front = raw[4:end]
    body = raw[end + 5:]
    metadata = yaml.safe_load(front) or {}
    return metadata, body


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    return any(p.match(stripped) for p in NOISE_LINE_PATTERNS)


def is_noise_paragraph(paragraph: str) -> bool:
    return any(p.search(paragraph) for p in NOISE_PARAGRAPH_PATTERNS)


def strip_noise(body: str) -> str:
    lines = [line for line in body.split("\n") if not is_noise_line(line)]
    text = "\n".join(lines)
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p for p in paragraphs if not is_noise_paragraph(p)]
    return "\n\n".join(paragraphs)


def split_into_sections(body: str) -> list[Section]:
    sections: list[Section] = []
    heading_stack: list[tuple[int, str]] = []
    current = Section(heading_path=["(intro)"])
    sections.append(current)

    for line in body.split("\n"):
        match = HEADER_RE.match(line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, title))
            path = [t for _, t in heading_stack]
            current = Section(heading_path=path)
            sections.append(current)
        else:
            current.lines.append(line)

    sections = [s for s in sections if s.text]
    return [
        s for s in sections
        if not any(p.match(h) for h in s.heading_path for p in NOISE_HEADING_PATTERNS)
    ]


def paragraph_fallback_split(section: Section, target_words: int = FALLBACK_TARGET_WORDS) -> list[Section]:
    """Split a header-less section into paragraph-boundary groups.

    Used when a doc has no real markdown headers (e.g. a blog whose
    "headings" were styled text that trafilatura didn't recognize),
    so header-splitting alone would leave the whole doc as one chunk.
    Never breaks a paragraph mid-way — groups whole paragraphs until
    the running total reaches target_words.
    """
    paragraphs = [p for p in re.split(r"\n\s*\n", section.text) if p.strip()]
    if len(paragraphs) <= 1:
        return [section]

    groups: list[list[str]] = []
    current: list[str] = []
    current_words = 0
    for paragraph in paragraphs:
        words = len(paragraph.split())
        if current and current_words + words > target_words:
            groups.append(current)
            current = []
            current_words = 0
        current.append(paragraph)
        current_words += words
    if current:
        groups.append(current)

    total = len(groups)
    return [
        Section(
            heading_path=section.heading_path + [f"part {i + 1}/{total}"],
            lines=["\n\n".join(group)],
        )
        for i, group in enumerate(groups)
    ]


def merge_small_sections(sections: list[Section]) -> list[Section]:
    merged: list[Section] = []
    for section in sections:
        if merged and section.word_count < MIN_CHUNK_WORDS:
            prev = merged[-1]
            prev.lines.append("")
            prev.lines.extend(section.lines)
            if section.heading_path != prev.heading_path:
                prev.heading_path = prev.heading_path + [
                    p for p in section.heading_path if p not in prev.heading_path
                ]
        else:
            merged.append(Section(heading_path=list(section.heading_path), lines=list(section.lines)))
    return merged


def heading_keywords(heading_path: list[str]) -> set[str]:
    words: set[str] = set()
    for heading in heading_path:
        for word in re.findall(r"[a-z0-9]+", heading.lower()):
            if word in STOPWORDS or word == "part":
                continue
            words.add(word)
            words |= HEADING_SYNONYMS.get(word, set())
    return words


def is_possibly_orphaned(section: Section) -> bool:
    if section.word_count < 30:
        return False
    if any(re.match(r"part \d+/\d+", h) or h == "(intro)" for h in section.heading_path):
        return False  # synthetic labels, not real headings to check content against
    keywords = heading_keywords(section.heading_path)
    if not keywords:
        return False
    body_words = {
        w for w in re.findall(r"[a-z0-9]+", section.text.lower()) if w not in STOPWORDS
    }
    overlap = keywords & body_words
    return len(overlap) == 0


def chunk_document(raw: str) -> list[Chunk]:
    metadata, body = parse_frontmatter(raw)
    body = strip_noise(body)
    sections = split_into_sections(body)
    if len(sections) <= 1 and sections and sections[0].word_count > FALLBACK_TARGET_WORDS:
        sections = paragraph_fallback_split(sections[0])
    sections = merge_small_sections(sections)

    chunks: list[Chunk] = []
    for i, section in enumerate(sections):
        chunks.append(
            Chunk(
                chunk_id=i,
                section_path=" > ".join(section.heading_path),
                text=section.text,
                word_count=section.word_count,
                possibly_orphaned=is_possibly_orphaned(section),
                metadata=metadata,
            )
        )
    return chunks
