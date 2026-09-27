import datetime
from unittest.mock import Mock, patch

import pytest

from app.services.chat_service import run_agent
from app.repositories.chat_history_repo import ChatMessage
from app.embeddings import EmbeddingError
from app.llm import LLMTurn, ToolCall
from app.services.knowledge_service import Snippet, UnknownDestinationError
from app.repositories.trips_repo import Trip, TripNotFoundError


class FakeLLMClient:
    """Returns pre-scripted turns in order, one per .chat() call."""

    def __init__(self, turns: list[LLMTurn]):
        self._turns = list(turns)
        self.calls: list[list[dict]] = []
        self.tools_offered: list[list[dict]] = []

    def chat(self, messages, tools):
        self.calls.append(messages)
        self.tools_offered.append(tools)
        return self._turns.pop(0)


def _tool_names(tools: list[dict]) -> set[str]:
    return {t["function"]["name"] for t in tools}


def test_final_text_answer_with_no_tool_call() -> None:
    llm = FakeLLMClient([LLMTurn(content="Hi there!")])
    assert run_agent("hello", llm=llm) == "Hi there!"


@patch("app.services.chat_service.search_destination_knowledge")
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


@patch("app.services.chat_service.search_destination_knowledge")
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


@patch("app.services.chat_service.search_destination_knowledge")
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


@patch("app.services.chat_service.search_destination_knowledge")
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


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages")
@patch("app.services.chat_service.get_trip")
def test_trip_id_injects_summary_and_history_into_context(
    mock_get_trip: Mock, mock_list_messages: Mock, mock_append_message: Mock, mock_list_days: Mock
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
    # Trip state + itinerary rules come after the replayed history (see run_agent).
    history_index = sent_messages.index({"role": "assistant", "content": "earlier answer"})
    summary_index = next(
        i for i, m in enumerate(sent_messages) if "Bangkok trip" in m["content"]
    )
    assert summary_index > history_index


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
def test_trip_id_persists_user_and_assistant_messages(
    mock_get_trip: Mock, mock_list_messages: Mock, mock_append_message: Mock, mock_list_days: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    llm = FakeLLMClient([LLMTurn(content="the reply")])

    run_agent("the question", llm=llm, conn=Mock(), trip_id=7)

    mock_append_message.assert_any_call(mock_get_trip.call_args[0][0], 7, "user", "the question")
    mock_append_message.assert_any_call(mock_get_trip.call_args[0][0], 7, "assistant", "the reply")


@patch("app.services.chat_service.get_trip", side_effect=TripNotFoundError("no trip with id 99"))
def test_unknown_trip_id_raises_without_calling_llm(mock_get_trip: Mock) -> None:
    llm = Mock()
    try:
        run_agent("hello", llm=llm, conn=Mock(), trip_id=99)
        assert False, "expected TripNotFoundError"
    except TripNotFoundError:
        pass
    llm.chat.assert_not_called()


@patch("app.services.chat_service.get_weather")
def test_get_weather_tool_call_result_fed_back_and_final_answer_returned(
    mock_get_weather: Mock,
) -> None:
    from app.services.weather_service import WeatherResult

    mock_get_weather.return_value = WeatherResult(
        source="forecast",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        avg_high_c=31.0,
        avg_low_c=25.0,
        total_precipitation_mm=2.0,
        days_sampled=2,
    )
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="get_weather",
                              arguments={"destination": "bangkok", "start_date": "2026-11-01",
                                         "end_date": "2026-11-02"})
                ],
            ),
            LLMTurn(content="Expect highs around 31C."),
        ]
    )

    result = run_agent("what's the weather in bangkok in november", llm=llm)

    assert result == "Expect highs around 31C."
    mock_get_weather.assert_called_once()
    tool_message = llm.calls[1][-1]
    assert tool_message["role"] == "tool"
    assert "forecast" in tool_message["content"]


def test_get_weather_tool_call_with_bad_date_returns_error_without_calling_service() -> None:
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="get_weather",
                              arguments={"destination": "bangkok", "start_date": "not-a-date",
                                         "end_date": "2026-11-02"})
                ],
            ),
            LLMTurn(content="Sorry, something went wrong with those dates."),
        ]
    )

    result = run_agent("weather?", llm=llm)

    assert result == "Sorry, something went wrong with those dates."
    tool_message = llm.calls[1][-1]
    assert "invalid date" in tool_message["content"]


@patch("app.services.chat_service.search_web")
def test_search_web_tool_call_result_fed_back_and_final_answer_returned(
    mock_search_web: Mock,
) -> None:
    from app.services.web_search_service import WebResult

    mock_search_web.return_value = [
        WebResult(rank=1, title="Paris guide", url="https://example.com", content="Mild weather.")
    ]
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="search_web", arguments={"query": "paris weather"})
                ],
            ),
            LLMTurn(content="From a quick search, Paris weather is mild."),
        ]
    )

    result = run_agent("what's paris like", llm=llm)

    assert result == "From a quick search, Paris weather is mild."
    mock_search_web.assert_called_once_with("paris weather")
    tool_message = llm.calls[1][-1]
    assert "Mild weather" in tool_message["content"]


@patch("app.services.chat_service.search_web")
def test_search_web_tool_error_fed_back_not_raised(mock_search_web: Mock) -> None:
    from app.services.web_search_service import TavilyError

    mock_search_web.side_effect = TavilyError("no key configured")
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="search_web", arguments={"query": "paris weather"})
                ],
            ),
            LLMTurn(content="Sorry, web search isn't available right now."),
        ]
    )

    result = run_agent("what's paris like", llm=llm)

    assert result == "Sorry, web search isn't available right now."
    tool_message = llm.calls[1][-1]
    assert "temporarily unavailable" in tool_message["content"]


@patch("app.services.chat_service.search_web", return_value=[])
def test_text_written_alongside_tool_calls_kept_in_reply(mock_search_web: Mock) -> None:
    llm = FakeLLMClient(
        [
            LLMTurn(
                content="Here's a 4-day plan.",
                tool_calls=[ToolCall(id="call_1", name="search_web", arguments={"query": "x"})],
            ),
            LLMTurn(content="Want me to change anything?"),
        ]
    )

    result = run_agent("plan it", llm=llm)

    assert result == "Here's a 4-day plan.\n\nWant me to change anything?"


@patch("app.services.chat_service.search_web", return_value=[])
def test_final_turn_repeating_interim_text_not_duplicated(mock_search_web: Mock) -> None:
    llm = FakeLLMClient(
        [
            LLMTurn(
                content="Here's the plan. Sound good?",
                tool_calls=[ToolCall(id="call_1", name="search_web", arguments={"query": "x"})],
            ),
            LLMTurn(content="Sound good?"),
        ]
    )

    assert run_agent("plan it", llm=llm) == "Here's the plan. Sound good?"


def test_empty_turn_is_retried_not_returned() -> None:
    llm = FakeLLMClient([LLMTurn(content=""), LLMTurn(content="Here you go.")])
    assert run_agent("hello", llm=llm) == "Here you go."
    assert len(llm.calls) == 2


def test_save_itinerary_day_not_offered_without_trip() -> None:
    llm = FakeLLMClient([LLMTurn(content="hi")])
    run_agent("hello", llm=llm)
    assert "save_itinerary_day" not in _tool_names(llm.tools_offered[0])


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.save_itinerary_day")
def test_save_itinerary_day_uses_current_trip_id_not_llm_args(
    mock_save: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    from app.repositories.itinerary_repo import ItineraryDay

    mock_get_trip.return_value = _fake_trip()
    mock_save.return_value = ItineraryDay(
        id=1, trip_id=5, day_number=3, plan={"title": "Sintra", "items": ["Pena"]},
        updated_at=datetime.datetime(2026, 1, 1),
    )
    conn = Mock()
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="save_itinerary_day",
                              arguments={"day": 3, "title": "Sintra", "items": ["Pena"],
                                         "trip_id": 999})
                ],
            ),
            LLMTurn(content="Added Sintra to day 3."),
        ]
    )

    result = run_agent("plan day 3", llm=llm, conn=conn, trip_id=5)

    assert result == "Added Sintra to day 3."
    assert "save_itinerary_day" in _tool_names(llm.tools_offered[0])
    mock_save.assert_called_once_with(conn, 5, day=3, title="Sintra", items=["Pena"])
    assert '"saved": true' in llm.calls[1][-1]["content"]


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.save_itinerary_day")
def test_invalid_itinerary_day_error_fed_back_not_raised(
    mock_save: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    from app.services.itinerary_service import InvalidItineraryDayError

    mock_get_trip.return_value = _fake_trip()
    mock_save.side_effect = InvalidItineraryDayError("day 9 is outside this trip's dates")
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="save_itinerary_day",
                              arguments={"day": 9, "title": "Extra", "items": []})
                ],
            ),
            LLMTurn(content="Your trip is only 6 days long."),
        ]
    )

    result = run_agent("add day 9", llm=llm, conn=Mock(), trip_id=1)

    assert result == "Your trip is only 6 days long."
    assert "outside this trip's dates" in llm.calls[1][-1]["content"]


def _trip_turn(tool_name: str, arguments: dict, final: str) -> FakeLLMClient:
    return FakeLLMClient(
        [
            LLMTurn(content=None,
                    tool_calls=[ToolCall(id="call_1", name=tool_name, arguments=arguments)]),
            LLMTurn(content=final),
        ]
    )


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.change_trip_dates")
def test_update_trip_dates_tool_parses_dates_and_reports_length(
    mock_change: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    mock_change.return_value = (
        _fake_trip(start_date=datetime.date(2026, 11, 6), end_date=datetime.date(2026, 11, 11)),
        [],
    )
    conn = Mock()
    llm = _trip_turn("update_trip_dates",
                     {"start_date": "2026-11-06", "end_date": "2026-11-11"}, "Extended.")

    run_agent("add 2 days", llm=llm, conn=conn, trip_id=5)

    mock_change.assert_called_once_with(
        conn, 5, datetime.date(2026, 11, 6), datetime.date(2026, 11, 11),
        drop_days_past_end=False,
    )
    assert '"days": 6' in llm.calls[1][-1]["content"]


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.change_trip_dates")
def test_update_trip_dates_drop_flag_passed_and_dropped_days_reported(
    mock_change: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    mock_change.return_value = (
        _fake_trip(start_date=datetime.date(2026, 11, 6), end_date=datetime.date(2026, 11, 8)),
        [4, 5],
    )
    llm = _trip_turn(
        "update_trip_dates",
        {"start_date": "2026-11-06", "end_date": "2026-11-08", "drop_days_past_end": True},
        "Trimmed to 3 days.",
    )

    run_agent("make it 3 days, drop the rest", llm=llm, conn=Mock(), trip_id=5)

    assert mock_change.call_args.kwargs == {"drop_days_past_end": True}
    assert '"dropped_days": [4, 5]' in llm.calls[1][-1]["content"]


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.change_trip_dates")
def test_drop_flag_ignored_when_user_did_not_ask_to_drop(
    mock_change: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    from app.services.itinerary_service import InvalidTripDatesError

    mock_get_trip.return_value = _fake_trip()
    mock_change.side_effect = InvalidTripDatesError("day(s) 4, 5 still have saved plans")
    llm = _trip_turn(
        "update_trip_dates",
        {"start_date": "2026-11-06", "end_date": "2026-11-08", "drop_days_past_end": True},
        "Want me to drop days 4 and 5?",
    )

    run_agent("Can we make the trip 3 days?", llm=llm, conn=Mock(), trip_id=5)

    assert mock_change.call_args.kwargs == {"drop_days_past_end": False}
    tool_content = llm.calls[1][-1]["content"]
    assert "drop_days_past_end was ignored" in tool_content
    assert "don't retry" in tool_content


@pytest.mark.parametrize(
    "message",
    ["Shorten to 3 days and drop the rest", "remove the last two days", "cut it to 3 days",
     "get rid of days 4 and 5", "yes, delete them"],
)
def test_drop_intent_recognised(message: str) -> None:
    from app.services.chat_service import _DROP_INTENT

    assert _DROP_INTENT.search(message)


@pytest.mark.parametrize(
    "message", ["Can we make the trip 3 days?", "shorten the trip please", "close to the beach"]
)
def test_no_drop_intent(message: str) -> None:
    from app.services.chat_service import _DROP_INTENT

    assert not _DROP_INTENT.search(message)


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.change_trip_dates")
def test_drop_flag_requires_real_boolean(
    mock_change: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    mock_change.return_value = (_fake_trip(), [])
    llm = _trip_turn(
        "update_trip_dates",
        {"start_date": "2026-11-06", "end_date": "2026-11-08", "drop_days_past_end": "false"},
        "ok",
    )

    run_agent("shorten", llm=llm, conn=Mock(), trip_id=5)

    assert mock_change.call_args.kwargs == {"drop_days_past_end": False}


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.change_trip_dates")
def test_update_trip_dates_bad_date_fed_back_without_calling_service(
    mock_change: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    llm = _trip_turn("update_trip_dates",
                     {"start_date": "next friday", "end_date": "2026-11-11"}, "Which dates?")

    run_agent("move it", llm=llm, conn=Mock(), trip_id=5)

    mock_change.assert_not_called()
    assert "invalid date" in llm.calls[1][-1]["content"]


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.change_trip_dates")
def test_shortening_refusal_fed_back_not_raised(
    mock_change: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    from app.services.itinerary_service import InvalidTripDatesError

    mock_get_trip.return_value = _fake_trip()
    mock_change.side_effect = InvalidTripDatesError("day(s) 4 still have saved plans")
    llm = _trip_turn("update_trip_dates",
                     {"start_date": "2026-11-06", "end_date": "2026-11-08"}, "Day 4 has plans.")

    assert run_agent("shorten it", llm=llm, conn=Mock(), trip_id=5) == "Day 4 has plans."
    assert "still have saved plans" in llm.calls[1][-1]["content"]


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.delete_itinerary_day")
def test_delete_itinerary_day_tool_uses_current_trip(
    mock_delete: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    conn = Mock()
    llm = _trip_turn("delete_itinerary_day", {"day": 2}, "Cleared day 2.")

    run_agent("drop day 2", llm=llm, conn=conn, trip_id=5)

    mock_delete.assert_called_once_with(conn, 5, 2)
    assert '"deleted": true' in llm.calls[1][-1]["content"]
    assert {"delete_itinerary_day", "update_trip_dates"} <= _tool_names(llm.tools_offered[0])


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.set_trip_details")
def test_update_trip_details_passes_only_given_fields(
    mock_set: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    mock_get_trip.return_value = _fake_trip()
    mock_set.return_value = _fake_trip(destinations=["da_nang_hoi_an"], party_size=2)
    conn = Mock()
    llm = _trip_turn(
        "update_trip_details",
        {"destinations": ["da_nang_hoi_an"], "party_size": 2},
        "Noted - two of you to Hoi An.",
    )

    run_agent("two of us going to hoi an", llm=llm, conn=conn, trip_id=5)

    mock_set.assert_called_once_with(
        conn, 5, destinations=["da_nang_hoi_an"], party_size=2,
        budget_planned=None, budget_total=None,
    )
    assert '"updated": true' in llm.calls[1][-1]["content"]
    assert "update_trip_details" in _tool_names(llm.tools_offered[0])


@patch("app.services.chat_service.list_days", return_value=[])
@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.set_trip_details")
def test_invalid_trip_details_fed_back_not_raised(
    mock_set: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    from app.services.trip_service import InvalidTripDetailsError

    mock_get_trip.return_value = _fake_trip()
    mock_set.side_effect = InvalidTripDetailsError("party_size must be a positive integer")
    llm = _trip_turn("update_trip_details", {"party_size": 0}, "How many of you?")

    assert run_agent("it's us", llm=llm, conn=Mock(), trip_id=5) == "How many of you?"
    assert "positive integer" in llm.calls[1][-1]["content"]


def test_trip_tools_not_offered_without_trip() -> None:
    llm = FakeLLMClient([LLMTurn(content="hi")])
    run_agent("hello", llm=llm)
    assert not {"delete_itinerary_day", "update_trip_dates"} & _tool_names(llm.tools_offered[0])


def test_save_itinerary_day_without_trip_returns_error() -> None:
    llm = FakeLLMClient(
        [
            LLMTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="save_itinerary_day",
                              arguments={"day": 1, "title": "x", "items": []})
                ],
            ),
            LLMTurn(content="Pick a trip first."),
        ]
    )

    run_agent("plan day 1", llm=llm)

    assert "no trip is selected" in llm.calls[1][-1]["content"]


@patch("app.services.chat_service.append_message")
@patch("app.services.chat_service.list_messages", return_value=[])
@patch("app.services.chat_service.get_trip")
@patch("app.services.chat_service.list_days")
def test_trip_context_includes_existing_itinerary(
    mock_list_days: Mock, mock_get_trip: Mock, *_: Mock
) -> None:
    from app.repositories.itinerary_repo import ItineraryDay

    mock_get_trip.return_value = _fake_trip()
    mock_list_days.return_value = [
        ItineraryDay(id=1, trip_id=1, day_number=1, plan={"title": "Arrive", "items": ["Hotel"]},
                     updated_at=datetime.datetime(2026, 1, 1)),
    ]
    llm = FakeLLMClient([LLMTurn(content="ok")])

    run_agent("what's on day 1?", llm=llm, conn=Mock(), trip_id=1)

    system_text = " ".join(m["content"] for m in llm.calls[0] if m["role"] == "system")
    assert "Day 1: Arrive (Hotel)" in system_text


def test_gives_up_after_max_tool_rounds() -> None:
    looping_turn = LLMTurn(
        content=None,
        tool_calls=[
            ToolCall(id="call_x", name="search_destination_knowledge",
                      arguments={"destination": "bangkok", "query": "x"})
        ],
    )
    llm = FakeLLMClient([looping_turn, looping_turn])
    with patch("app.services.chat_service.search_destination_knowledge", return_value=[]):
        result = run_agent("loop forever", llm=llm, max_tool_rounds=2)
    assert "rephrase" in result
