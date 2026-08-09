"""Tests for eligibility-first Chroma retrieval and Top-K behavior."""

from collections.abc import Sequence
from pathlib import Path

import pytest

from benefitwise.employee import EmployeeContext
from benefitwise.policy import PolicyChunk
from benefitwise.policy_parser import load_policy_chunks
from benefitwise.retrieval import PolicyRetriever, has_explicit_job_level_scope
from benefitwise.vector_store import VectorMatch
from tests.fakes import KeywordEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RecordingVectorStore:
    """Record the exact candidate boundary passed from deterministic filtering."""

    def __init__(self) -> None:
        self.synchronized_policy_ids: tuple[str, ...] = ()
        self.candidate_policy_ids: tuple[str, ...] = ()

    def synchronize(self, policies: Sequence[PolicyChunk]) -> None:
        self.synchronized_policy_ids = tuple(policy.policy_id for policy in policies)

    def query(
        self,
        query_texts: Sequence[str],
        *,
        candidate_policy_ids: Sequence[str],
    ) -> tuple[tuple[VectorMatch, ...], ...]:
        self.candidate_policy_ids = tuple(candidate_policy_ids)
        matches = tuple(VectorMatch(policy_id, 1.0) for policy_id in candidate_policy_ids)
        return tuple(matches for _ in query_texts)


class WeakReformulationVectorStore(RecordingVectorStore):
    """Return a weak agent match and a strong original-question match."""

    def query(
        self,
        query_texts: Sequence[str],
        *,
        candidate_policy_ids: Sequence[str],
    ) -> tuple[tuple[VectorMatch, ...], ...]:
        self.candidate_policy_ids = tuple(candidate_policy_ids)
        target = "MED-COVERED-GENERAL-JL2-8"
        return (
            (VectorMatch(target, 0.24),),
            (VectorMatch(target, 0.31),),
        )


class PolicyScopeRankingVectorStore(RecordingVectorStore):
    """Model query drifts to IPD while the original question asks about OPD."""

    def query(
        self,
        query_texts: Sequence[str],
        *,
        candidate_policy_ids: Sequence[str],
    ) -> tuple[tuple[VectorMatch, ...], ...]:
        self.candidate_policy_ids = tuple(candidate_policy_ids)
        return (
            (
                VectorMatch("MED-IPD-GENERAL-JL2-8", 0.90),
                VectorMatch("MED-OPD-GENERAL-JL2-8", 0.30),
            ),
            (
                VectorMatch("MED-OPD-GENERAL-JL2-8", 0.40),
                VectorMatch("MED-IPD-GENERAL-JL2-8", 0.30),
            ),
        )


@pytest.fixture
def policies():
    return load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")


@pytest.mark.parametrize(
    ("employee", "expected_policy", "expected_amount"),
    [
        (
            EmployeeContext("E001", "JL3", "TH", "DEMO", "General"),
            "MED-OPD-GENERAL-JL2-8",
            "14,250",
        ),
        (
            EmployeeContext("E002", "JL6", "TH", "DEMO", "General"),
            "MED-OPD-GENERAL-JL2-8",
            "14,250",
        ),
        (
            EmployeeContext("E003", "JL1", "TH", "DEMO", "Operations"),
            "MED-OPD-OPERATIONS-JL1",
            "300",
        ),
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
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    evidence = retriever.retrieve("What is my allowance for clinic visits?", employee)

    assert evidence[0].policy_id == "MED-OPD-GENERAL-JL2-8"


def test_eligibility_filter_becomes_vector_database_candidate_filter(policies) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    vector_store = RecordingVectorStore()
    retriever = PolicyRetriever(
        policies,
        KeywordEmbeddings(),
        min_similarity=0.1,
        vector_store=vector_store,
    )

    retriever.retrieve("outpatient medical", employee)

    assert set(vector_store.synchronized_policy_ids) == {
        policy.policy_id for policy in policies
    }
    assert "MED-OPD-GENERAL-JL2-8" in vector_store.candidate_policy_ids
    assert "MED-OPD-OPERATIONS-JL1" not in vector_store.candidate_policy_ids


def test_policy_information_can_return_another_group_with_applicability_tag(
    policies,
) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    evidence = retriever.retrieve_policy_information(
        "operations social security policy",
        employee,
    )

    assert "MED-CLAIM-OPERATIONS-JL1" in {
        item.policy_id for item in evidence
    }
    assert all(item.applies_to_current_employee is False for item in evidence)


def test_explicit_level_narrows_policy_information_candidates_by_policy_range(
    policies,
) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    vector_store = RecordingVectorStore()
    retriever = PolicyRetriever(
        policies,
        KeywordEmbeddings(),
        min_similarity=0.1,
        vector_store=vector_store,
    )

    evidence = retriever.retrieve_policy_information("What does JL8 receive?", employee)

    assert "MED-OPD-GENERAL-JL2-8" in vector_store.candidate_policy_ids
    assert "MED-OPD-OPERATIONS-JL1" not in vector_store.candidate_policy_ids
    assert all(item.applies_to_current_employee is True for item in evidence)


def test_explicit_policy_scope_ranks_by_original_question_not_model_drift(
    policies,
) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    retriever = PolicyRetriever(
        policies,
        KeywordEmbeddings(),
        min_similarity=0.1,
        vector_store=PolicyScopeRankingVectorStore(),
    )

    evidence = retriever.retrieve_policy_information(
        "inpatient benefit",
        employee,
        reference_query="What can JL8 claim for outpatient treatment?",
    )

    assert [item.policy_id for item in evidence] == [
        "MED-OPD-GENERAL-JL2-8",
        "MED-IPD-GENERAL-JL2-8",
    ]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("What does JL8 receive?", True),
        ('What does "JL"8 receive?', True),
        ("What is my OPD limit?", False),
    ],
)
def test_detects_explicit_job_level_policy_scope(query: str, expected: bool) -> None:
    assert has_explicit_job_level_scope(query) is expected


def test_top_k_limits_ranked_results(policies) -> None:
    employee = EmployeeContext("E002", "JL6", "TH", "DEMO", "General")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    evidence = retriever.retrieve("What medical benefits do I have?", employee, top_k=2)

    assert len(evidence) == 2
    assert evidence[0].similarity_score >= evidence[1].similarity_score


def test_irrelevant_query_returns_no_evidence(policies) -> None:
    employee = EmployeeContext("E003", "JL1", "TH", "DEMO", "Operations")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)

    assert retriever.retrieve("Where can I park my car?", employee) == ()


def test_original_query_anchors_agent_reformulation(policies) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    embeddings = KeywordEmbeddings()
    retriever = PolicyRetriever(policies, embeddings, min_similarity=0.1)

    evidence = retriever.retrieve(
        "outpatient medical benefit",
        employee,
        reference_query="annual leave days",
    )

    assert evidence == ()
    assert embeddings.batches[-1] == [
        "outpatient medical benefit",
        "annual leave days",
    ]


def test_original_query_recovers_a_weak_but_relevant_reformulation(policies) -> None:
    employee = EmployeeContext("E002", "JL6", "TH", "DEMO", "General")
    vector_store = WeakReformulationVectorStore()
    retriever = PolicyRetriever(
        policies,
        KeywordEmbeddings(),
        min_similarity=0.26,
        vector_store=vector_store,
    )

    evidence = retriever.retrieve(
        "emergency ambulance coverage as a medical expense",
        employee,
        reference_query="Is an emergency ambulance a covered medical expense?",
    )

    assert [item.policy_id for item in evidence] == ["MED-COVERED-GENERAL-JL2-8"]
    assert evidence[0].similarity_score == pytest.approx(0.31)


def test_employee_with_no_eligible_policies_skips_embedding(policies) -> None:
    employee = EmployeeContext("X001", "JL6", "SG", "DEMO", "General")
    embeddings = KeywordEmbeddings()
    retriever = PolicyRetriever(policies, embeddings)

    assert retriever.retrieve("annual leave", employee) == ()
    assert embeddings.batches == []


@pytest.mark.parametrize(("query", "error"), [("", ValueError), (None, TypeError)])
def test_rejects_invalid_query(policies, query, error) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    retriever = PolicyRetriever(policies, KeywordEmbeddings())

    with pytest.raises(error):
        retriever.retrieve(query, employee)


@pytest.mark.parametrize(("top_k", "error"), [(0, ValueError), (1.5, TypeError), (True, TypeError)])
def test_rejects_invalid_top_k(policies, top_k, error) -> None:
    employee = EmployeeContext("E001", "JL3", "TH", "DEMO", "General")
    retriever = PolicyRetriever(policies, KeywordEmbeddings())

    with pytest.raises(error):
        retriever.retrieve("annual leave", employee, top_k=top_k)
