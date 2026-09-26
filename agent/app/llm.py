"""Provider-agnostic chat-with-tools interface.

OllamaLLMClient is the only implementation for now (local, no API
key/cost). An AnthropicLLMClient implementing the same LLMClient
protocol can be added later (Messages API tool use) without changing
app/agent.py - that's the seam this interface exists for.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

import requests

from app.embeddings import DEFAULT_BASE_URL

DEFAULT_CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "gemma4:latest")


class LLMError(Exception):
    """Typed error for chat-completion failures (server unreachable, bad response, etc.)."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMTurn:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> LLMTurn: ...


class OllamaLLMClient:
    def __init__(self, model: str = DEFAULT_CHAT_MODEL, base_url: str = DEFAULT_BASE_URL):
        self.model = model
        self.base_url = base_url

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMTurn:
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "tools": tools, "stream": False},
                timeout=120.0,
            )
        except requests.RequestException as e:
            raise LLMError(
                f"could not reach Ollama at {self.base_url} (is `ollama serve` running?): {e}"
            ) from e

        if response.status_code != 200:
            raise LLMError(f"Ollama returned {response.status_code}: {response.text}")

        data = response.json()
        message = data.get("message")
        if message is None:
            raise LLMError(f"unexpected Ollama response shape: {data}")

        tool_calls = [
            ToolCall(
                id=tc.get("id", f"call_{i}"),
                name=tc["function"]["name"],
                arguments=tc["function"]["arguments"],
            )
            for i, tc in enumerate(message.get("tool_calls") or [])
        ]
        return LLMTurn(content=message.get("content") or None, tool_calls=tool_calls)
