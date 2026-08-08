"""Tests for retrieval dataset validation and metric calculations."""

import json

import pytest

from benefitwise.employee import EmployeeContext
from benefitwise.evaluation import RetrievalCase, evaluate_retrieval, load_retrieval_cases
from benefitwise.policy import PolicyEligibility
from benefitwise.retrieval import PolicyEvidence

_ANY_ELIGIBILITY = PolicyEligibility(
    countries=frozenset({"*"}),
    companies=frozenset({"*"}),
    employee_types=frozenset({"*"}),
    min_job_level=1,
    max_job_level=10,
)


class MappingRetriever:
    def __init__(self, results: dict[str, tuple[str, ...]]) -> None:
        self.results = results

    def retrieve(self, query, employee, *, top_k=3):
        return tuple(_evidence(policy_id) for policy_id in self.results[query][:top_k])


def _evidence(policy_id: str) -> PolicyEvidence:
    return PolicyEvidence(
        policy_id=policy_id,
        title=policy_id,
        excerpt="Evidence",
        eligibility=_ANY_ELIGIBILITY,
        similarity_score=1.0,
    )


def _employee_resolver(employee_id: str) -> EmployeeContext:
    return EmployeeContext(employee_id, "JL3", "TH", "DEMO", "General")


def test_calculates_hit_at_k_mrr_and_negative_accuracy() -> None:
    cases = (
        RetrievalCase("rank-1", "E001", "q1", frozenset({"P1"})),
        RetrievalCase("rank-2", "E001", "q2", frozenset({"P2"})),
        RetrievalCase("miss", "E001", "q3", frozenset({"P3"})),
        RetrievalCase("negative-pass", "E001", "q4", frozenset()),
        RetrievalCase("negative-fail", "E001", "q5", frozenset()),
    )
    retriever = MappingRetriever(
        {"q1": ("P1",), "q2": ("PX", "P2"), "q3": (), "q4": (), "q5": ("PX",)}
    )

    result = evaluate_retrieval(retriever, _employee_resolver, cases, top_k=3)

    assert result.metrics.hit_at_1 == pytest.approx(1 / 3)
    assert result.metrics.hit_at_k == pytest.approx(2 / 3)
    assert result.metrics.mrr == pytest.approx(0.5)
    assert result.metrics.no_evidence_accuracy == pytest.approx(0.5)


def test_loads_committed_dataset_shape(tmp_path) -> None:
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "case-1",
                    "employee_id": "E001",
                    "query": "annual leave",
                    "expected_policy_ids": ["LEAVE-1"],
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_retrieval_cases(dataset_path)

    assert cases[0].expected_policy_ids == frozenset({"LEAVE-1"})


def test_rejects_duplicate_case_ids(tmp_path) -> None:
    dataset_path = tmp_path / "cases.json"
    duplicated_case = {
        "case_id": "duplicate",
        "employee_id": "E001",
        "query": "annual leave",
        "expected_policy_ids": ["P1"],
    }
    dataset_path.write_text(json.dumps([duplicated_case, duplicated_case]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_retrieval_cases(dataset_path)
