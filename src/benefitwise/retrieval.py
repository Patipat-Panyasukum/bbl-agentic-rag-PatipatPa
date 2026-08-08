"""Eligibility-first semantic retrieval for employee benefit policies."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benefitwise.embeddings import EmbeddingProvider
from benefitwise.employee import EmployeeContext
from benefitwise.policy import PolicyChunk, PolicyEligibility, filter_eligible_policies
from benefitwise.vector_store import ChromaPolicyVectorStore, PolicyVectorStore

DEFAULT_MIN_SIMILARITY = 0.26


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
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
        chroma_path: str | Path | None = None,
        chroma_client: Any | None = None,
        collection_name: str | None = None,
        embedding_model_id: str | None = None,
        vector_store: PolicyVectorStore | None = None,
    ) -> None:
        if not -1.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between -1.0 and 1.0")
        self._policies = tuple(policies)
        policy_ids = [policy.policy_id for policy in self._policies]
        if len(policy_ids) != len(set(policy_ids)):
            raise ValueError("policy IDs must be unique")
        self._policies_by_id = {
            policy.policy_id: policy for policy in self._policies
        }
        if vector_store is not None and any(
            value is not None
            for value in (
                chroma_path,
                chroma_client,
                collection_name,
                embedding_model_id,
            )
        ):
            raise ValueError(
                "vector_store cannot be combined with Chroma construction options"
            )
        self._vector_store = vector_store or ChromaPolicyVectorStore(
            embedding_provider,
            path=chroma_path,
            client=chroma_client,
            collection_name=collection_name,
            embedding_model_id=embedding_model_id,
        )
        self.min_similarity = min_similarity

    def retrieve(
        self,
        query: str,
        employee: EmployeeContext,
        *,
        top_k: int = 3,
        reference_query: str | None = None,
    ) -> tuple[PolicyEvidence, ...]:
        """Return eligible, relevant policy evidence in deterministic rank order."""

        normalized_query = _validate_query(query)
        normalized_reference = (
            _validate_query(reference_query) if reference_query is not None else None
        )
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise TypeError("top_k must be an integer")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        # This ordering is a security and business-rule boundary. Only IDs
        # admitted here are passed into Chroma's metadata candidate filter.
        eligible_policies = filter_eligible_policies(self._policies, employee)
        if not eligible_policies:
            return ()

        query_texts = [normalized_query]
        if normalized_reference and normalized_reference != normalized_query:
            query_texts.append(normalized_reference)
        self._vector_store.synchronize(self._policies)
        match_sets = self._vector_store.query(
            query_texts,
            candidate_policy_ids=[policy.policy_id for policy in eligible_policies],
        )
        primary_matches = match_sets[0]
        reference_scores = (
            {
                match.policy_id: match.similarity_score
                for match in match_sets[1]
            }
            if len(match_sets) == 2
            else {
                match.policy_id: match.similarity_score
                for match in primary_matches
            }
        )

        # When an agent reformulates the search, the original question remains
        # a relevance anchor so generic added words cannot create evidence.
        evidence: list[PolicyEvidence] = []
        for match in primary_matches:
            reference_score = reference_scores.get(match.policy_id, -1.0)
            if (
                match.similarity_score < self.min_similarity
                or reference_score < self.min_similarity
            ):
                continue
            policy = self._policies_by_id[match.policy_id]
            evidence.append(
                PolicyEvidence(
                    policy_id=policy.policy_id,
                    title=policy.title,
                    excerpt=policy.content,
                    eligibility=policy.eligibility,
                    similarity_score=match.similarity_score,
                )
            )
        return tuple(evidence[:top_k])


def _validate_query(query: str) -> str:
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be blank")
    return normalized_query
