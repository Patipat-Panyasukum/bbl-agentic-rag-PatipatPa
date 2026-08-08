"""Reproducible retrieval evaluation with Hit@K and MRR metrics."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from benefitwise.employee import EmployeeContext
from benefitwise.retrieval import PolicyEvidence

DEFAULT_EVALUATION_PATH = Path("eval/retrieval_cases.json")


class Retriever(Protocol):
    """Retrieval interface required by the evaluation runner."""

    def retrieve(
        self,
        query: str,
        employee: EmployeeContext,
        *,
        top_k: int = 3,
    ) -> Sequence[PolicyEvidence]: ...


@dataclass(frozen=True, slots=True)
class RetrievalCase:
    case_id: str
    employee_id: str
    query: str
    expected_policy_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class RetrievalCaseResult:
    case_id: str
    expected_policy_ids: tuple[str, ...]
    retrieved_policy_ids: tuple[str, ...]
    first_relevant_rank: int | None
    passed: bool


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    hit_at_1: float
    hit_at_k: float
    mrr: float
    no_evidence_accuracy: float | None
    positive_cases: int
    negative_cases: int
    top_k: int


@dataclass(frozen=True, slots=True)
class RetrievalEvaluation:
    metrics: RetrievalMetrics
    cases: tuple[RetrievalCaseResult, ...]


def load_retrieval_cases(
    dataset_path: str | Path = DEFAULT_EVALUATION_PATH,
) -> tuple[RetrievalCase, ...]:
    """Load and validate the committed retrieval evaluation dataset."""

    raw_cases = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("evaluation dataset must be a non-empty JSON array")

    cases: list[RetrievalCase] = []
    seen_ids: set[str] = set()
    for index, raw_case in enumerate(raw_cases, start=1):
        if not isinstance(raw_case, dict):
            raise ValueError(f"evaluation case {index} must be a JSON object")
        required = {"case_id", "employee_id", "query", "expected_policy_ids"}
        if set(raw_case) != required:
            raise ValueError(f"evaluation case {index} must contain exactly {sorted(required)}")

        case_id = _required_string(raw_case["case_id"], "case_id", index)
        if case_id in seen_ids:
            raise ValueError(f"duplicate evaluation case_id '{case_id}'")
        seen_ids.add(case_id)

        expected_ids = raw_case["expected_policy_ids"]
        if not isinstance(expected_ids, list) or not all(
            isinstance(policy_id, str) and policy_id.strip() for policy_id in expected_ids
        ):
            raise ValueError(f"expected_policy_ids in case {index} must be a string array")

        cases.append(
            RetrievalCase(
                case_id=case_id,
                employee_id=_required_string(raw_case["employee_id"], "employee_id", index),
                query=_required_string(raw_case["query"], "query", index),
                expected_policy_ids=frozenset(expected_ids),
            )
        )
    return tuple(cases)


def evaluate_retrieval(
    retriever: Retriever,
    employee_resolver: Callable[[str], EmployeeContext],
    cases: Sequence[RetrievalCase],
    *,
    top_k: int = 3,
) -> RetrievalEvaluation:
    """Evaluate ranked retrieval and unsupported-query abstention separately."""

    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if not cases:
        raise ValueError("at least one evaluation case is required")

    results: list[RetrievalCaseResult] = []
    positive_ranks: list[int | None] = []
    negative_passes: list[bool] = []

    for case in cases:
        employee = employee_resolver(case.employee_id)
        evidence = retriever.retrieve(case.query, employee, top_k=top_k)
        retrieved_ids = tuple(item.policy_id for item in evidence)
        rank = _first_relevant_rank(retrieved_ids, case.expected_policy_ids)

        if case.expected_policy_ids:
            # Positive cases contribute to Hit@K and MRR denominators.
            positive_ranks.append(rank)
            passed = rank is not None
        else:
            # Negative cases measure whether the threshold correctly abstains.
            passed = not retrieved_ids
            negative_passes.append(passed)

        results.append(
            RetrievalCaseResult(
                case_id=case.case_id,
                expected_policy_ids=tuple(sorted(case.expected_policy_ids)),
                retrieved_policy_ids=retrieved_ids,
                first_relevant_rank=rank,
                passed=passed,
            )
        )

    if not positive_ranks:
        raise ValueError("evaluation requires at least one positive case")

    positive_count = len(positive_ranks)
    metrics = RetrievalMetrics(
        hit_at_1=sum(rank == 1 for rank in positive_ranks) / positive_count,
        hit_at_k=sum(rank is not None for rank in positive_ranks) / positive_count,
        mrr=sum(0.0 if rank is None else 1.0 / rank for rank in positive_ranks)
        / positive_count,
        no_evidence_accuracy=(
            sum(negative_passes) / len(negative_passes) if negative_passes else None
        ),
        positive_cases=positive_count,
        negative_cases=len(negative_passes),
        top_k=top_k,
    )
    return RetrievalEvaluation(metrics=metrics, cases=tuple(results))


def _first_relevant_rank(
    retrieved_policy_ids: Sequence[str],
    expected_policy_ids: frozenset[str],
) -> int | None:
    for rank, policy_id in enumerate(retrieved_policy_ids, start=1):
        if policy_id in expected_policy_ids:
            return rank
    return None


def _required_string(value: object, field_name: str, case_index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} in case {case_index} must be a non-empty string")
    return value.strip()
