import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from run_eval import fact_mentioned, score_question  # noqa: E402

from app.tools import Snippet, UnknownDestinationError  # noqa: E402


def test_fact_mentioned_true_on_close_paraphrase() -> None:
    fact = "Nathan Tailors (127 Tran Hung Dao Street)"
    reply = "You should check out 8 Nathan Tailors on Tran Hung Dao Street."
    assert fact_mentioned(fact, reply.lower())


def test_fact_mentioned_false_when_absent() -> None:
    fact = "suits start from US$129"
    reply = "Hoi An has some lovely beaches nearby."
    assert not fact_mentioned(fact, reply.lower())


def test_fact_mentioned_numeric_fact() -> None:
    fact = "taxi costs roughly 300,000-500,000 dong"
    reply = "a taxi will run you about 300,000 to 500,000 dong"
    assert fact_mentioned(fact, reply.lower())


@patch("run_eval.run_agent")
@patch("run_eval.search_destination_knowledge")
def test_score_question_normal_records_hit_rank_and_facts(
    mock_search: Mock, mock_run_agent: Mock
) -> None:
    mock_search.return_value = [
        Snippet(rank=1, text="x", source_url="u", source_file="other.md", section_path="A", distance=0.1),
        Snippet(rank=2, text="x", source_url="u", source_file="target.md", section_path="B", distance=0.2),
    ]
    mock_run_agent.return_value = "Nathan Tailors is great, suits from $129."

    q = {
        "id": "q06",
        "category": "shopping",
        "destination": "da_nang_hoi_an",
        "question": "tailors?",
        "expected_source_files": ["target.md"],
        "key_facts": ["Nathan Tailors", "suits from about US$129", "something not mentioned at all here"],
    }
    result = score_question(q, conn=None, retrieval_only=False)

    assert result["retrieval_hit_rank"] == 2
    assert result["tool_error"] is None
    assert result["key_facts_total"] == 3
    assert result["key_facts_hit"] == 2


@patch("run_eval.search_destination_knowledge")
def test_score_question_unknown_destination_records_tool_error(mock_search: Mock) -> None:
    mock_search.side_effect = UnknownDestinationError("'bali' is not covered")
    q = {
        "id": "q18",
        "category": "adversarial-out-of-scope",
        "destination": "bali",
        "question": "best beach?",
        "expected_source_files": [],
        "key_facts": [],
    }
    result = score_question(q, conn=None, retrieval_only=True)

    assert result["tool_error"] is not None
    assert result["correctly_refused_at_tool_level"] is True
    assert result["retrieval_hit_rank"] is None


@patch("run_eval.search_destination_knowledge")
def test_score_question_empty_corpus_flagged(mock_search: Mock) -> None:
    mock_search.return_value = []
    q = {
        "id": "q19",
        "category": "adversarial-empty-corpus",
        "destination": "bangkok",
        "question": "street food?",
        "expected_source_files": [],
        "key_facts": [],
    }
    result = score_question(q, conn=None, retrieval_only=True)

    assert result["zero_snippets_returned"] is True


@patch("run_eval.run_agent")
@patch("run_eval.search_destination_knowledge")
def test_retrieval_only_skips_agent_call(mock_search: Mock, mock_run_agent: Mock) -> None:
    mock_search.return_value = []
    q = {
        "id": "q01",
        "category": "transport",
        "destination": "da_nang_hoi_an",
        "question": "x?",
        "expected_source_files": ["a.md"],
        "key_facts": ["fact"],
    }
    result = score_question(q, conn=None, retrieval_only=True)

    mock_run_agent.assert_not_called()
    assert result["reply"] is None
    assert result["key_facts_hit"] is None
