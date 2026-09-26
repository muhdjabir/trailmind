from unittest.mock import Mock, patch

from app.agent import run_agent
from app.embeddings import EmbeddingError
from app.llm import LLMTurn, ToolCall
from app.tools import Snippet, UnknownDestinationError


class FakeLLMClient:
    """Returns pre-scripted turns in order, one per .chat() call."""

    def __init__(self, turns: list[LLMTurn]):
        self._turns = list(turns)
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools):
        self.calls.append(messages)
        return self._turns.pop(0)


def test_final_text_answer_with_no_tool_call() -> None:
    llm = FakeLLMClient([LLMTurn(content="Hi there!")])
    assert run_agent("hello", llm=llm) == "Hi there!"


@patch("app.agent.search_destination_knowledge")
def test_tool_call_result_fed_back_and_final_answer_returned(mock_search: Mock) -> None:
    mock_search.return_value = [
        Snippet(rank=1, text="Tailor shops...", source_url="https://x", source_file="x.md", section_path="Buy", distance=0.2)
    ]
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="search_destination_knowledge",
                              arguments={"destination": "da_nang_hoi_an", "query": "tailors"})
                ],
            ),
            LLMTurn(content="Try Nathan Tailors."),
        ]
    )

    result = run_agent("best tailors in hoi an", llm=llm)

    assert result == "Try Nathan Tailors."
    assert len(llm.calls) == 2
    tool_message = llm.calls[1][-1]
    assert tool_message["role"] == "tool"
    assert "Tailor shops" in tool_message["content"]


@patch("app.agent.search_destination_knowledge")
def test_unknown_destination_error_fed_back_to_llm(mock_search: Mock) -> None:
    mock_search.side_effect = UnknownDestinationError("'bali' is not covered")
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="search_destination_knowledge",
                              arguments={"destination": "bali", "query": "beaches"})
                ],
            ),
            LLMTurn(content="Sorry, I don't have information on Bali."),
        ]
    )

    result = run_agent("beaches in bali", llm=llm)

    assert result == "Sorry, I don't have information on Bali."
    tool_message = llm.calls[1][-1]
    assert "not covered" in tool_message["content"]


@patch("app.agent.search_destination_knowledge")
def test_embedding_error_fed_back_as_tool_result_not_raised(mock_search: Mock) -> None:
    mock_search.side_effect = EmbeddingError("ollama down")
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="search_destination_knowledge",
                              arguments={"destination": "bangkok", "query": "food"})
                ],
            ),
            LLMTurn(content="Something went wrong looking that up."),
        ]
    )

    result = run_agent("street food in bangkok", llm=llm)

    assert result == "Something went wrong looking that up."
    tool_message = llm.calls[1][-1]
    assert "temporarily unavailable" in tool_message["content"]


def test_gives_up_after_max_tool_rounds() -> None:
    looping_turn = LLMTurn(
        content=None,
        tool_calls=[
            ToolCall(id="call_x", name="search_destination_knowledge",
                      arguments={"destination": "bangkok", "query": "x"})
        ],
    )
    llm = FakeLLMClient([looping_turn, looping_turn])
    with patch("app.agent.search_destination_knowledge", return_value=[]):
        result = run_agent("loop forever", llm=llm, max_tool_rounds=2)
    assert "rephrase" in result
