"""Persistent Chroma index for policy-clause embeddings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from threading import Lock
from typing import Any, Protocol

import chromadb
from chromadb.config import Settings as ChromaSettings
import numpy as np
from numpy.typing import NDArray

from benefitwise.embeddings import EmbeddingProvider
from benefitwise.policy import PolicyChunk

DEFAULT_CHROMA_PATH = Path("data/chroma")
DEFAULT_COLLECTION_PREFIX = "benefitwise-policies-v1"
CHUNKING_STRATEGY = "numbered-policy-clause"
CHUNK_OVERLAP = 0


class _ChromaClient(Protocol):
    def get_or_create_collection(self, *args: Any, **kwargs: Any) -> Any:
        """Return a Chroma collection."""


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """A policy identifier and its cosine similarity from Chroma."""

    policy_id: str
    similarity_score: float


class PolicyVectorStore(Protocol):
    """Boundary used by retrieval so filtering can be tested independently."""

    def synchronize(self, policies: Sequence[PolicyChunk]) -> None:
        """Make the generated vector index match the source policies."""

    def query(
        self,
        query_texts: Sequence[str],
        *,
        candidate_policy_ids: Sequence[str],
    ) -> tuple[tuple[VectorMatch, ...], ...]:
        """Rank only the supplied candidate policy identifiers."""


class ChromaPolicyVectorStore:
    """Synchronize policy clauses and rank a caller-supplied candidate set."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        *,
        path: str | Path | None = None,
        client: _ChromaClient | None = None,
        collection_name: str | None = None,
        embedding_model_id: str | None = None,
    ) -> None:
        if path is not None and client is not None:
            raise ValueError("path and client are mutually exclusive")

        self._embedding_provider = embedding_provider
        self.embedding_model_id = embedding_model_id or _embedding_identity(
            embedding_provider
        )
        self.collection_name = collection_name or _collection_name(
            self.embedding_model_id
        )
        if client is not None:
            self._client = client
        elif path is not None:
            self._client = chromadb.PersistentClient(
                path=str(path), settings=_local_chroma_settings()
            )
        else:
            self._client = chromadb.EphemeralClient(
                settings=_local_chroma_settings()
            )
        # Embeddings are always supplied by our configured provider. Disabling
        # Chroma's default function prevents an accidental model download.
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            configuration={"hnsw": {"space": "cosine"}},
            embedding_function=None,
        )
        self._sync_lock = Lock()
        self._synchronized = False

    def synchronize(self, policies: Sequence[PolicyChunk]) -> None:
        """Upsert changed clauses and remove stale generated index records."""

        if self._synchronized:
            return

        with self._sync_lock:
            if self._synchronized:
                return

            policy_list = list(policies)
            _require_unique_policy_ids(policy_list)
            existing = self._collection.get(include=["metadatas"])
            existing_ids = list(existing.get("ids") or [])
            existing_metadatas = list(existing.get("metadatas") or [])
            stored_fingerprints = {
                policy_id: str((metadata or {}).get("fingerprint", ""))
                for policy_id, metadata in zip(
                    existing_ids, existing_metadatas, strict=True
                )
            }

            changed = [
                policy
                for policy in policy_list
                if stored_fingerprints.get(policy.policy_id)
                != _policy_fingerprint(policy, self.embedding_model_id)
            ]
            if changed:
                vectors = np.asarray(
                    self._embedding_provider.embed(
                        [policy.searchable_text for policy in changed]
                    ),
                    dtype=np.float32,
                )
                _validate_embedding_shape(vectors, expected_rows=len(changed))
                self._collection.upsert(
                    ids=[policy.policy_id for policy in changed],
                    embeddings=vectors.tolist(),
                    documents=[policy.searchable_text for policy in changed],
                    metadatas=[
                        _policy_metadata(policy, self.embedding_model_id)
                        for policy in changed
                    ],
                )

            current_ids = {policy.policy_id for policy in policy_list}
            stale_ids = sorted(set(existing_ids) - current_ids)
            if stale_ids:
                # These are generated vector-index rows only; source policy files
                # remain authoritative and are never modified by synchronization.
                self._collection.delete(ids=stale_ids)

            self._synchronized = True

    def query(
        self,
        query_texts: Sequence[str],
        *,
        candidate_policy_ids: Sequence[str],
    ) -> tuple[tuple[VectorMatch, ...], ...]:
        """Rank only the policy IDs supplied by the deterministic caller."""

        texts = list(query_texts)
        candidate_ids = list(dict.fromkeys(candidate_policy_ids))
        if not texts:
            return ()
        if not candidate_ids:
            return tuple(() for _ in texts)

        query_vectors = np.asarray(
            self._embedding_provider.embed(texts), dtype=np.float32
        )
        _validate_embedding_shape(query_vectors, expected_rows=len(texts))

        # `policy_id $in [...]` is the vector-database pre-filter. Chroma applies
        # it to the deterministic candidate set before cosine ranking.
        result = self._collection.query(
            query_embeddings=query_vectors.tolist(),
            n_results=len(candidate_ids),
            where={"policy_id": {"$in": candidate_ids}},
            include=["distances"],
        )
        result_ids = list(result.get("ids") or [])
        result_distances = list(result.get("distances") or [])
        if len(result_ids) != len(texts) or len(result_distances) != len(texts):
            raise RuntimeError(
                "Chroma returned an unexpected number of query results"
            )

        matches: list[tuple[VectorMatch, ...]] = []
        for policy_ids, distances in zip(
            result_ids, result_distances, strict=True
        ):
            if len(policy_ids) != len(distances):
                raise RuntimeError("Chroma returned mismatched IDs and distances")
            query_matches = [
                VectorMatch(
                    policy_id=policy_id,
                    similarity_score=_cosine_distance_to_similarity(distance),
                )
                for policy_id, distance in zip(policy_ids, distances, strict=True)
            ]
            query_matches.sort(
                key=lambda match: (-match.similarity_score, match.policy_id)
            )
            matches.append(tuple(query_matches))
        return tuple(matches)


def _embedding_identity(provider: EmbeddingProvider) -> str:
    model_name = getattr(provider, "model_name", None)
    if isinstance(model_name, str) and model_name.strip():
        return model_name.strip()
    provider_type = type(provider)
    return f"{provider_type.__module__}.{provider_type.__qualname__}"


def _local_chroma_settings() -> ChromaSettings:
    """Keep the assignment index local without anonymized product telemetry."""

    return ChromaSettings(anonymized_telemetry=False)


def _collection_name(embedding_model_id: str) -> str:
    model_digest = hashlib.sha256(
        embedding_model_id.encode("utf-8")
    ).hexdigest()[:12]
    return f"{DEFAULT_COLLECTION_PREFIX}-{model_digest}"


def _policy_fingerprint(policy: PolicyChunk, embedding_model_id: str) -> str:
    payload = {
        "embedding_model": embedding_model_id,
        "policy_id": policy.policy_id,
        "searchable_text": policy.searchable_text,
        "eligibility": policy.eligibility.as_dict(),
        "chunking_strategy": CHUNKING_STRATEGY,
        "chunk_overlap": CHUNK_OVERLAP,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _policy_metadata(
    policy: PolicyChunk, embedding_model_id: str
) -> dict[str, str | int]:
    eligibility = policy.eligibility
    return {
        "policy_id": policy.policy_id,
        "title": policy.title,
        "countries": "|".join(sorted(eligibility.countries)),
        "companies": "|".join(sorted(eligibility.companies)),
        "employee_types": "|".join(sorted(eligibility.employee_types)),
        "min_job_level": eligibility.min_job_level,
        "max_job_level": eligibility.max_job_level,
        "embedding_model": embedding_model_id,
        "chunking_strategy": CHUNKING_STRATEGY,
        "chunk_overlap": CHUNK_OVERLAP,
        "fingerprint": _policy_fingerprint(policy, embedding_model_id),
    }


def _cosine_distance_to_similarity(distance: float) -> float:
    # A cosine-configured Chroma collection reports distance = 1 - similarity.
    return max(-1.0, min(1.0, 1.0 - float(distance)))


def _validate_embedding_shape(
    embeddings: NDArray[np.float32], *, expected_rows: int
) -> None:
    if embeddings.ndim != 2:
        raise ValueError("embedding provider must return a two-dimensional array")
    if embeddings.shape[0] != expected_rows:
        raise ValueError(
            "embedding provider returned an unexpected number of embedding rows"
        )
    if embeddings.shape[1] == 0:
        raise ValueError("embedding provider returned empty embedding vectors")


def _require_unique_policy_ids(policies: Sequence[PolicyChunk]) -> None:
    policy_ids = [policy.policy_id for policy in policies]
    if len(policy_ids) != len(set(policy_ids)):
        raise ValueError("policy IDs must be unique before vector indexing")
