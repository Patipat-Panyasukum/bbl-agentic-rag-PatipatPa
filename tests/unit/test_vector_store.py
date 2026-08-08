"""Tests for the local Chroma policy-vector index."""

from dataclasses import replace
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings
import pytest

from benefitwise.policy import PolicyChunk, PolicyEligibility
from benefitwise.vector_store import (
    CHUNK_OVERLAP,
    CHUNKING_STRATEGY,
    ChromaPolicyVectorStore,
)
from tests.fakes import KeywordEmbeddings


def _policy(policy_id: str, content: str) -> PolicyChunk:
    return PolicyChunk(
        policy_id=policy_id,
        title=content,
        content=content,
        eligibility=PolicyEligibility(
            countries=frozenset({"TH"}),
            companies=frozenset({"DEMO"}),
            employee_types=frozenset({"GENERAL"}),
            min_job_level=1,
            max_job_level=8,
        ),
        search_terms=(content,),
    )


def _store(provider: KeywordEmbeddings, client):
    return ChromaPolicyVectorStore(
        provider,
        client=client,
        collection_name=f"test-policy-index-{uuid4().hex}",
        embedding_model_id="keyword-test-v1",
    )


def _client():
    return chromadb.EphemeralClient(
        settings=ChromaSettings(anonymized_telemetry=False)
    )


def test_metadata_candidate_filter_runs_before_cosine_ranking() -> None:
    client = _client()
    store = _store(KeywordEmbeddings(), client)
    matching = _policy("POLICY-OPD", "outpatient")
    admitted = _policy("POLICY-PARKING", "parking")
    store.synchronize((matching, admitted))

    matches = store.query(
        ["outpatient"],
        candidate_policy_ids=[admitted.policy_id],
    )[0]

    assert [match.policy_id for match in matches] == [admitted.policy_id]
    assert matches[0].similarity_score == pytest.approx(0.0)


def test_cosine_collection_reports_similarity_instead_of_distance() -> None:
    store = _store(KeywordEmbeddings(), _client())
    policy = _policy("POLICY-OPD", "outpatient")
    store.synchronize((policy,))

    match = store.query(["outpatient"], candidate_policy_ids=[policy.policy_id])[0][0]

    assert match.similarity_score == pytest.approx(1.0)


def test_generated_index_records_chunking_metadata() -> None:
    client = _client()
    store = _store(KeywordEmbeddings(), client)
    policy = _policy("POLICY-OPD", "outpatient")
    store.synchronize((policy,))

    record = client.get_collection(store.collection_name).get(
        ids=[policy.policy_id], include=["metadatas"]
    )

    metadata = record["metadatas"][0]
    assert metadata["chunking_strategy"] == CHUNKING_STRATEGY
    assert metadata["chunk_overlap"] == CHUNK_OVERLAP == 0


def test_unchanged_index_reuses_document_embeddings() -> None:
    client = _client()
    collection_name = f"test-policy-index-{uuid4().hex}"
    policy = _policy("POLICY-OPD", "outpatient")
    first_provider = KeywordEmbeddings()
    first = ChromaPolicyVectorStore(
        first_provider,
        client=client,
        collection_name=collection_name,
        embedding_model_id="keyword-test-v1",
    )
    first.synchronize((policy,))

    second_provider = KeywordEmbeddings()
    second = ChromaPolicyVectorStore(
        second_provider,
        client=client,
        collection_name=collection_name,
        embedding_model_id="keyword-test-v1",
    )
    second.synchronize((policy,))

    assert len(first_provider.batches) == 1
    assert second_provider.batches == []


def test_sync_reembeds_changed_policy_and_removes_stale_record() -> None:
    client = _client()
    collection_name = f"test-policy-index-{uuid4().hex}"
    original = _policy("POLICY-OPD", "outpatient")
    stale = _policy("POLICY-STALE", "parking")
    first = ChromaPolicyVectorStore(
        KeywordEmbeddings(),
        client=client,
        collection_name=collection_name,
        embedding_model_id="keyword-test-v1",
    )
    first.synchronize((original, stale))

    changed_provider = KeywordEmbeddings()
    second = ChromaPolicyVectorStore(
        changed_provider,
        client=client,
        collection_name=collection_name,
        embedding_model_id="keyword-test-v1",
    )
    second.synchronize((replace(original, content="outpatient clinic"),))

    assert changed_provider.batches == [["outpatient\noutpatient clinic\noutpatient"]]
    records = client.get_collection(collection_name).get(include=[])
    assert records["ids"] == [original.policy_id]
