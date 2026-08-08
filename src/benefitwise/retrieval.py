"""Eligibility-first semantic retrieval for employee benefit policies."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from benefitwise.embeddings import EmbeddingProvider
from benefitwise.employee import EmployeeContext
from benefitwise.policy import PolicyChunk, PolicyEligibility, filter_eligible_policies


@dataclass(frozen=True, slots=True)
class PolicyEvidence:
    """A ranked raw policy snippet returned by the retrieval boundary."""

    policy_id: str
    title: str
    excerpt: str
    eligibility: PolicyEligibility
    similarity_score: float

    def as_dict(self) -> dict[str, object]:
        """Return stable structured evidence for LangChain tool artifacts."""

        return {
            "policy_id": self.policy_id,
            "title": self.title,
            "excerpt": self.excerpt,
            "eligibility": self.eligibility.as_dict(),
            "similarity_score": self.similarity_score,
        }


class PolicyRetriever:
    """Filter policy access deterministically, then perform semantic ranking."""

    def __init__(
        self,
        policies: Sequence[PolicyChunk],
        embedding_provider: EmbeddingProvider,
        *,
        min_similarity: float = 0.26,
    ) -> None:
        if not -1.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between -1.0 and 1.0")
        self._policies = tuple(policies)
        self._embedding_provider = embedding_provider
        self.min_similarity = min_similarity

    def retrieve(
        self,
        query: str,
        employee: EmployeeContext,
        *,
        top_k: int = 3,
    ) -> tuple[PolicyEvidence, ...]:
        """Return eligible, relevant policy evidence in deterministic rank order."""

        normalized_query = _validate_query(query)
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise TypeError("top_k must be an integer")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        # This ordering is a security and business-rule boundary: ineligible
        # content must never enter embedding or similarity ranking.
        eligible_policies = filter_eligible_policies(self._policies, employee)
        if not eligible_policies:
            return ()

        texts = [normalized_query]
        texts.extend(policy.searchable_text for policy in eligible_policies)
        embeddings = np.asarray(self._embedding_provider.embed(texts), dtype=np.float32)
        _validate_embedding_shape(embeddings, expected_rows=len(texts))

        scores = cosine_similarities(embeddings[0], embeddings[1:])
        ranked = sorted(
            zip(eligible_policies, scores, strict=True),
            key=lambda item: (-float(item[1]), item[0].policy_id),
        )

        evidence = [
            PolicyEvidence(
                policy_id=policy.policy_id,
                title=policy.title,
                excerpt=policy.content,
                eligibility=policy.eligibility,
                similarity_score=float(score),
            )
            for policy, score in ranked
            if float(score) >= self.min_similarity
        ]
        return tuple(evidence[:top_k])


def cosine_similarities(
    query_vector: NDArray[np.floating],
    candidate_vectors: NDArray[np.floating],
) -> NDArray[np.float32]:
    """Compute cosine similarity safely, returning zero for zero-norm vectors."""

    query = np.asarray(query_vector, dtype=np.float32)
    candidates = np.asarray(candidate_vectors, dtype=np.float32)
    if query.ndim != 1:
        raise ValueError("query_vector must be one-dimensional")
    if candidates.ndim != 2:
        raise ValueError("candidate_vectors must be two-dimensional")
    if candidates.shape[1] != query.shape[0]:
        raise ValueError("query and candidate embedding dimensions must match")

    query_norm = np.linalg.norm(query)
    candidate_norms = np.linalg.norm(candidates, axis=1)
    denominators = candidate_norms * query_norm
    dot_products = candidates @ query
    similarities = np.divide(
        dot_products,
        denominators,
        out=np.zeros_like(dot_products, dtype=np.float32),
        where=denominators > 0,
    )
    return np.clip(similarities, -1.0, 1.0).astype(np.float32)


def _validate_query(query: str) -> str:
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be blank")
    return normalized_query


def _validate_embedding_shape(
    embeddings: NDArray[np.float32],
    *,
    expected_rows: int,
) -> None:
    if embeddings.ndim != 2:
        raise ValueError("embedding provider must return a two-dimensional array")
    if embeddings.shape[0] != expected_rows:
        raise ValueError(
            "embedding provider returned an unexpected number of embedding rows"
        )
    if embeddings.shape[1] == 0:
        raise ValueError("embedding provider returned empty embedding vectors")
