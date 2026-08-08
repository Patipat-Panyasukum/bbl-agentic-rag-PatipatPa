"""Deterministic test doubles for external or model-backed components."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray


class KeywordEmbeddings:
    """Small semantic test double with explicit synonym groups."""

    _CONCEPTS = (
        ("outpatient", "clinic", "doctor visit"),
        ("inpatient", "hospital admission", "hospitalized"),
        ("dental", "dentist", "teeth"),
        ("annual leave", "vacation", "days off"),
        ("international", "overseas"),
        ("travel", "flight", "trip"),
        ("medical", "health"),
        ("parking", "car park"),
    )

    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        text_list = list(texts)
        self.batches.append(text_list)
        vectors = [self._embed_one(text) for text in text_list]
        return np.asarray(vectors, dtype=np.float32)

    def _embed_one(self, text: str) -> list[float]:
        normalized_text = text.lower()
        return [
            1.0 if any(term in normalized_text for term in terms) else 0.0
            for terms in self._CONCEPTS
        ]
