"""Tests for the OpenAI embedding adapter without network access."""

import numpy as np
import pytest

from benefitwise.embeddings import OpenAIEmbeddingProvider


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(texts)
        return [[float(index), 1.0] for index, _ in enumerate(texts, start=1)]


def test_embeds_one_vector_per_text_with_injected_client() -> None:
    client = FakeEmbeddingClient()
    provider = OpenAIEmbeddingProvider(client=client)

    vectors = provider.embed(["query", "eligible policy context"])

    assert client.batches == [["query", "eligible policy context"]]
    assert vectors.dtype == np.float32
    np.testing.assert_allclose(vectors, [[1.0, 1.0], [2.0, 1.0]])


def test_empty_batch_skips_provider_call() -> None:
    client = FakeEmbeddingClient()
    provider = OpenAIEmbeddingProvider(client=client)

    vectors = provider.embed([])

    assert vectors.shape == (0, 0)
    assert client.batches == []


def test_rejects_blank_model_name() -> None:
    with pytest.raises(ValueError, match="model_name"):
        OpenAIEmbeddingProvider(" ")
