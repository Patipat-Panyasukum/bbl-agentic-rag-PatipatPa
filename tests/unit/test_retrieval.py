"""Tests for eligibility-first cosine retrieval and Top-K behavior."""

from pathlib import Path

import numpy as np
import pytest

from benefitwise.employee import EmployeeContext
from benefitwise.policy_parser import load_policy_chunks
from benefitwise.retrieval import PolicyRetriever, cosine_similarities
from tests.fakes import KeywordEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def policies():
    return load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")


@pytest.mark.parametrize(
    ("employee", "expected_policy", "expected_amount"),
    [
        (EmployeeContext("E001", "JL3", "TH", "BBL", "Permanent"), "MED-OPD-JL1-4", "20,000"),
        (EmployeeContext("E002", "JL6", "TH", "BBL", "Permanent"), "MED-OPD-JL5-7", "40,000"),
        (EmployeeContext("E003", "JL9", "TH", "BBL", "Permanent"), "MED-OPD-JL8-10", "80,000"),
    ],
)
def test_same_opd_query_returns_employee_specific_policy(
    policies,
    employee: EmployeeContext,
    expected_policy: str,
    expected_amount: str,
) -> None:
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    evidence = retriever.retrieve(
        "How much can I claim for outpatient medical expenses?",
        employee,
        top_k=1,
    )

    assert evidence[0].policy_id == expected_policy
    assert expected_amount in evidence[0].excerpt


def test_paraphrased_query_retrieves_relevant_policy(policies) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "BBL", "Permanent")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    evidence = retriever.retrieve("What is my allowance for clinic visits?", employee)

    assert evidence[0].policy_id == "MED-OPD-JL1-4"


def test_eligibility_filter_runs_before_embedding(policies) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "BBL", "Permanent")
    embeddings = KeywordEmbeddings()
    retriever = PolicyRetriever(policies, embeddings, min_similarity=0.1)

    retriever.retrieve("outpatient medical", employee)

    embedded_policy_text = "\n".join(embeddings.batches[0][1:])
    assert "Outpatient medical benefit for JL1-JL4" in embedded_policy_text
    assert "Outpatient medical benefit for JL5-JL7" not in embedded_policy_text
    assert "International business travel" not in embedded_policy_text


def test_top_k_limits_ranked_results(policies) -> None:
    employee = EmployeeContext("E002", "JL6", "TH", "BBL", "Permanent")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    evidence = retriever.retrieve("What medical benefits do I have?", employee, top_k=2)

    assert len(evidence) == 2
    assert evidence[0].similarity_score >= evidence[1].similarity_score


def test_irrelevant_query_returns_no_evidence(policies) -> None:
    employee = EmployeeContext("E003", "JL9", "TH", "BBL", "Permanent")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    assert retriever.retrieve("Where can I park my car?", employee) == ()


def test_employee_with_no_eligible_policies_skips_embedding(policies) -> None:
    employee = EmployeeContext("X001", "JL6", "SG", "BBL", "Permanent")
    embeddings = KeywordEmbeddings()
    retriever = PolicyRetriever(policies, embeddings)

    assert retriever.retrieve("annual leave", employee) == ()
    assert embeddings.batches == []


@pytest.mark.parametrize(("query", "error"), [("", ValueError), (None, TypeError)])
def test_rejects_invalid_query(policies, query, error) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "BBL", "Permanent")
    retriever = PolicyRetriever(policies, KeywordEmbeddings())

    with pytest.raises(error):
        retriever.retrieve(query, employee)


@pytest.mark.parametrize(("top_k", "error"), [(0, ValueError), (1.5, TypeError), (True, TypeError)])
def test_rejects_invalid_top_k(policies, top_k, error) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "BBL", "Permanent")
    retriever = PolicyRetriever(policies, KeywordEmbeddings())

    with pytest.raises(error):
        retriever.retrieve("annual leave", employee, top_k=top_k)


def test_cosine_similarities_handles_zero_vectors() -> None:
    scores = cosine_similarities(
        np.asarray([1.0, 0.0], dtype=np.float32),
        np.asarray([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]], dtype=np.float32),
    )

    np.testing.assert_allclose(scores, [1.0, 0.0, 0.0])
