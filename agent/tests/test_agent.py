import datetime
from unittest.mock import Mock, patch

from app.agent import run_agent
from app.chat_history import ChatMessage
from app.embeddings import EmbeddingError
from app.llm import LLMTurn, ToolCall
from app.tools import Snippet, UnknownDestinationError
from app.trips import Trip, TripNotFoundError


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


@patch("app.agent.search_destination_knowledge")
def test_zero_snippets_fed_back_as_explicit_no_information_signal(mock_search: Mock) -> None:
    mock_search.return_value = []
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="search_destination_knowledge",
                              arguments={"destination": "bangkok", "query": "street food"})
                ],
            ),
            LLMTurn(content="I don't have specifics on that."),
        ]
    )

    result = run_agent("street food in bangkok", llm=llm)

    assert result == "I don't have specifics on that."
    tool_message = llm.calls[1][-1]
    assert "no_information_found" in tool_message["content"]
    assert "snippets" not in tool_message["content"]


def _fake_trip(**overrides) -> Trip:
    defaults = dict(
        id=1,
        user_id=None,
        name="Bangkok trip",
        destinations=["bangkok"],
        start_date=None,
        end_date=None,
        party_size=None,
        status="draft",
        budget_planned=None,
        budget_total=None,
        created_at=datetime.datetime(2026, 1, 1),
        updated_at=datetime.datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return Trip(**defaults)


@patch("app.agent.append_message")
@patch("app.agent.list_messages")
@patch("app.agent.get_trip")
def test_trip_id_injects_summary_and_history_into_context(
    mock_get_trip: Mock, mock_list_messages: Mock, mock_append_message: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip(name="Bangkok trip")
    mock_list_messages.return_value = [
        ChatMessage(id=1, trip_id=1, role="user", content="earlier question",
                    created_at=datetime.datetime(2026, 1, 1)),
        ChatMessage(id=2, trip_id=1, role="assistant", content="earlier answer",
                    created_at=datetime.datetime(2026, 1, 1)),
    ]
    llm = FakeLLMClient([LLMTurn(content="Here's more info.")])

    result = run_agent("follow-up question", llm=llm, conn=Mock(), trip_id=1)

    assert result == "Here's more info."
    sent_messages = llm.calls[0]
    assert any("Bangkok trip" in m["content"] for m in sent_messages if m["role"] == "system")
    assert {"role": "user", "content": "earlier question"} in sent_messages
    assert {"role": "assistant", "content": "earlier answer"} in sent_messages
    assert sent_messages[-1] == {"role": "user", "content": "follow-up question"}


@patch("app.agent.append_message")
@patch("app.agent.list_messages", return_value=[])
@patch("app.agent.get_trip")
def test_trip_id_persists_user_and_assistant_messages(
    mock_get_trip: Mock, mock_list_messages: Mock, mock_append_message: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    llm = FakeLLMClient([LLMTurn(content="the reply")])

    run_agent("the question", llm=llm, conn=Mock(), trip_id=7)

    mock_append_message.assert_any_call(mock_get_trip.call_args[0][0], 7, "user", "the question")
    mock_append_message.assert_any_call(mock_get_trip.call_args[0][0], 7, "assistant", "the reply")


@patch("app.agent.get_trip", side_effect=TripNotFoundError("no trip with id 99"))
def test_unknown_trip_id_raises_without_calling_llm(mock_get_trip: Mock) -> None:
    llm = Mock()
    try:
        run_agent("hello", llm=llm, conn=Mock(), trip_id=99)
        assert False, "expected TripNotFoundError"
    except TripNotFoundError:
        pass
    llm.chat.assert_not_called()


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
