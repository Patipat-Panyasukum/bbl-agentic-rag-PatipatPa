"""Embedding adapters used by semantic policy retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingProvider(Protocol):
    """Small interface that keeps deterministic tests free of API calls."""

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Return one embedding row for each input text."""


class _DocumentEmbeddingClient(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return provider vectors for a batch of documents."""


class OpenAIEmbeddingProvider:
    """Lazy OpenAI sentence/context embedding provider for policy retrieval."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        base_url: str | None = None,
        client: _DocumentEmbeddingClient | None = None,
    ) -> None:
        normalized_model = model_name.strip()
        if not normalized_model:
            raise ValueError("model_name must not be blank")

        self.model_name = normalized_model
        self.base_url = base_url
        self._client = client

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        text_list = list(texts)
        if not text_list:
            return np.empty((0, 0), dtype=np.float32)

        # Initialization stays lazy so policy/parser tests do not require an
        # API key. The runtime still sends only eligibility-filtered content.
        if self._client is None:
            from langchain_openai import OpenAIEmbeddings

            self._client = OpenAIEmbeddings(
                model=self.model_name,
                base_url=self.base_url,
                max_retries=2,
                timeout=60,
            )

        vectors = self._client.embed_documents(text_list)
        return np.asarray(vectors, dtype=np.float32)
