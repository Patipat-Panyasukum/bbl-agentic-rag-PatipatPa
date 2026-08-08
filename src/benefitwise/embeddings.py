"""Embedding adapters used by semantic policy retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingProvider(Protocol):
    """Small interface that keeps retrieval testable without a model download."""

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """Return one embedding row for each input text."""


class SentenceTransformerEmbeddings:
    """Lazy local sentence-transformer embedding provider."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        text_list = list(texts)
        if not text_list:
            return np.empty((0, 0), dtype=np.float32)

        # Loading is lazy so parser and eligibility tests never download or
        # initialize a machine-learning model.
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

        vectors = self._model.encode(
            text_list,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)
