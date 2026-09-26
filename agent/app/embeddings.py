"""Generate embeddings via a local Ollama server.

Model: nomic-embed-text (pulled locally, no API key/cost). Ollama's
/api/embed endpoint accepts a batch of inputs in one request.
"""

from __future__ import annotations

import os

import requests

DEFAULT_MODEL = "nomic-embed-text"
# Overridable via env: containerized (docker compose) runs need
# host.docker.internal since Ollama runs natively on the host, not
# in a container.
DEFAULT_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


class EmbeddingError(Exception):
    """Typed error for embedding failures (Ollama unreachable, bad response, etc.)."""


def embed_texts(
    texts: list[str],
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 60.0,
) -> list[list[float]]:
    if not texts:
        return []

    try:
        response = requests.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": texts},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise EmbeddingError(
            f"could not reach Ollama at {base_url} (is `ollama serve` running?): {e}"
        ) from e

    if response.status_code != 200:
        raise EmbeddingError(
            f"Ollama returned {response.status_code} for model '{model}': {response.text}"
        )

    data = response.json()
    embeddings = data.get("embeddings")
    if embeddings is None or len(embeddings) != len(texts):
        raise EmbeddingError(
            f"unexpected Ollama response shape for model '{model}': {data}"
        )
    return embeddings
