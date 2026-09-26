"""Score the agent against eval/questions.yaml (v0 step 14).

Three axes, per docs/implementation_list.md:
  - retrieval quality: does a chunk from `expected_source_files` land
    in the tool's top-5 for this question?
  - answer quality: does the final reply mention the substance of each
    `key_facts` entry? (heuristic keyword-overlap check, not exact
    match - paraphrasing is expected and fine)
  - hallucination rate: for the two adversarial questions, did the
    system refuse/admit-ignorance correctly rather than inventing
    specifics?

Requires the same runtime deps as the live service: Ollama reachable
(embeddings + chat) and Postgres reachable. Each question does a full
agent round-trip, so this is slow (~15-25s/question locally) - it's a
manual/periodic check, not something to run on every commit.

Usage:
    python scripts/run_eval.py                  # full eval (slow)
    python scripts/run_eval.py --retrieval-only # skip the LLM, just score retrieval (fast)
    python scripts/run_eval.py --id q06 q16      # run specific questions only
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from app.agent import run_agent
from app.tools import UnknownDestinationError, search_destination_knowledge
from app.vector_store import get_connection

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "eval" / "questions.yaml"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "eval" / "results"


def fact_mentioned(fact: str, reply_lower: str) -> bool:
    """Heuristic: does the reply contain most of this fact's distinctive words?

    Not exact-match by design - answers are expected to paraphrase.
    Short/common words are ignored in favor of numbers and longer words
    (names, prices, place names), which carry most of a fact's signal.
    """
    tokens = re.findall(r"[a-z0-9']+", fact.lower())
    content_tokens = [t for t in tokens if len(t) > 3 or t.isdigit()]
    if not content_tokens:
        content_tokens = tokens
    if not content_tokens:
        return False
    hits = sum(1 for t in content_tokens if t in reply_lower)
    return (hits / len(content_tokens)) >= 0.5


def score_question(q: dict, conn, retrieval_only: bool) -> dict:
    result: dict = {"id": q["id"], "category": q["category"], "question": q["question"]}
    expected_sources = q.get("expected_source_files") or []

    try:
        snippets = search_destination_knowledge(q["destination"], q["question"], top_k=5, conn=conn)
        result["tool_error"] = None
    except UnknownDestinationError as e:
        snippets = []
        result["tool_error"] = str(e)

    result["retrieved_sources"] = [s.source_file for s in snippets]

    if expected_sources:
        hit_rank = next(
            (i + 1 for i, s in enumerate(snippets) if s.source_file in expected_sources), None
        )
        result["retrieval_hit_rank"] = hit_rank
    else:
        result["retrieval_hit_rank"] = None  # not applicable (adversarial)

    if q["category"] == "adversarial-out-of-scope":
        result["correctly_refused_at_tool_level"] = result["tool_error"] is not None
    if q["category"] == "adversarial-empty-corpus":
        result["zero_snippets_returned"] = len(snippets) == 0

    if retrieval_only:
        result["reply"] = None
        result["key_facts_hit"] = None
        result["key_facts_total"] = None
        return result

    result["reply"] = run_agent(q["question"], conn=conn)
    reply_lower = result["reply"].lower()

    key_facts = q.get("key_facts") or []
    fact_hits = [fact_mentioned(f, reply_lower) for f in key_facts]
    result["key_facts_total"] = len(key_facts)
    result["key_facts_hit"] = sum(fact_hits)
    result["key_facts_detail"] = list(zip(key_facts, fact_hits))

    return result


def print_summary(results: list[dict], retrieval_only: bool) -> None:
    print("\n=== Retrieval quality ===")
    n_applicable = sum(1 for r in results if r["id"] not in ("q18", "q19"))
    n_hit = sum(1 for r in results if r["retrieval_hit_rank"] is not None)
    print(f"{n_hit}/{n_applicable} questions had an expected source in the top-5")
    for r in results:
        if r["id"] in ("q18", "q19"):
            continue
        mark = "OK" if r["retrieval_hit_rank"] else "MISS"
        print(f"  [{mark:4}] {r['id']} rank={r['retrieval_hit_rank']}  {r['question'][:60]}")

    print("\n=== Adversarial checks ===")
    for r in results:
        if r["id"] == "q18":
            print(f"  q18 (out-of-scope destination): tool_error={'yes' if r['tool_error'] else 'NO'}")
        if r["id"] == "q19":
            print(f"  q19 (known, empty corpus): zero_snippets={r.get('zero_snippets_returned')}")

    if retrieval_only:
        return

    print("\n=== Answer quality (key-fact coverage, heuristic) ===")
    total_facts = sum(r["key_facts_total"] for r in results if r["key_facts_total"])
    total_hit = sum(r["key_facts_hit"] for r in results if r["key_facts_hit"] is not None)
    if total_facts:
        print(f"{total_hit}/{total_facts} key facts detected across all answers")
    for r in results:
        if not r["key_facts_total"]:
            continue
        print(f"  {r['id']}: {r['key_facts_hit']}/{r['key_facts_total']}  {r['question'][:60]}")

    print("\n=== Adversarial replies (read manually for hallucination) ===")
    for r in results:
        if r["id"] in ("q18", "q19"):
            print(f"\n  {r['id']}: {r['question']}")
            print(f"  -> {r['reply']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", nargs="+", help="Only run these question ids (e.g. q06 q16)")
    parser.add_argument(
        "--retrieval-only", action="store_true", help="Skip the LLM, score retrieval only (fast)"
    )
    args = parser.parse_args()

    questions = yaml.safe_load(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if args.id:
        questions = [q for q in questions if q["id"] in args.id]

    conn = get_connection()
    results = []
    for q in questions:
        print(f"[{q['id']}] {q['question']}")
        results.append(score_question(q, conn, args.retrieval_only))
    conn.close()

    print_summary(results, args.retrieval_only)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{datetime.datetime.now():%Y%m%d-%H%M%S}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull results written to {out_path.relative_to(RESULTS_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
