from unittest.mock import Mock, patch

import pytest
import requests

from app.llm import LLMError, OllamaLLMClient


@patch("app.llm.requests.post")
def test_parses_tool_call_response(mock_post: Mock) -> None:
    mock_post.return_value = Mock(
        status_code=200,
        json=lambda: {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "search_destination_knowledge",
                            "arguments": {"destination": "bangkok", "query": "street food"},
                        },
                    }
                ],
            }
        },
    )
    turn = OllamaLLMClient().chat(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert turn.content is None
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].name == "search_destination_knowledge"
    assert turn.tool_calls[0].arguments == {"destination": "bangkok", "query": "street food"}


@patch("app.llm.requests.post")
def test_parses_plain_text_response(mock_post: Mock) -> None:
    mock_post.return_value = Mock(
        status_code=200,
        json=lambda: {"message": {"role": "assistant", "content": "Hello!"}},
    )
    turn = OllamaLLMClient().chat(messages=[], tools=[])
    assert turn.content == "Hello!"
    assert turn.tool_calls == []


@patch("app.llm.requests.post")
def test_connection_error_raises_llm_error(mock_post: Mock) -> None:
    mock_post.side_effect = requests.ConnectionError("refused")
    with pytest.raises(LLMError, match="ollama serve"):
        OllamaLLMClient().chat(messages=[], tools=[])


@patch("app.llm.requests.post")
def test_non_200_raises_llm_error(mock_post: Mock) -> None:
    mock_post.return_value = Mock(status_code=500, text="boom")
    with pytest.raises(LLMError, match="500"):
        OllamaLLMClient().chat(messages=[], tools=[])
