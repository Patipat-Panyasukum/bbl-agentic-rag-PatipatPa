"""Deterministic end-to-end evaluation for the BenefitWise agent workflow."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from langchain_core.runnables import RunnableConfig

from benefitwise.agents import INSUFFICIENT_INFORMATION_RESPONSE

DEFAULT_AGENT_EVALUATION_PATH = Path("eval/agent_cases.json")

_CITATION_PATTERN = re.compile(r"\[([A-Z][A-Z0-9-]+)\]")
_THAI_PATTERN = re.compile(r"[\u0E00-\u0E7F]")


class AgentGraph(Protocol):
    """Graph interface required by the local evaluation runner."""

    def invoke(
        self,
        input: dict[str, str],
        config: RunnableConfig | None = None,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class AgentCase:
    case_id: str
    employee_id: str
    query: str
    expected_policy_ids: frozenset[str]
    required_answer_terms: tuple[str, ...]
    expected_language: str
    should_abstain: bool


@dataclass(frozen=True, slots=True)
class AgentCaseResult:
    case_id: str
    retrieval_query: str
    retrieved_policy_ids: tuple[str, ...]
    cited_policy_ids: tuple[str, ...]
    evidence_match: bool
    citation_match: bool
    fact_match: bool
    language_match: bool
    grounding_valid: bool
    abstention_match: bool
    passed: bool
    answer: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AgentMetrics:
    evidence_accuracy: float
    citation_accuracy: float
    required_fact_accuracy: float
    language_accuracy: float
    grounding_pass_rate: float
    abstention_accuracy: float | None
    overall_pass_rate: float
    positive_cases: int
    negative_cases: int


@dataclass(frozen=True, slots=True)
class AgentEvaluation:
    metrics: AgentMetrics
    cases: tuple[AgentCaseResult, ...]


RunConfigFactory = Callable[[AgentCase], RunnableConfig]


def load_agent_cases(
    dataset_path: str | Path = DEFAULT_AGENT_EVALUATION_PATH,
) -> tuple[AgentCase, ...]:
    """Load and validate the committed full-workflow evaluation dataset."""

    raw_cases = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("agent evaluation dataset must be a non-empty JSON array")

    cases: list[AgentCase] = []
    seen_ids: set[str] = set()
    required_fields = {
        "case_id",
        "employee_id",
        "query",
        "expected_policy_ids",
        "required_answer_terms",
        "expected_language",
        "should_abstain",
    }

    for index, raw_case in enumerate(raw_cases, start=1):
        if not isinstance(raw_case, dict) or set(raw_case) != required_fields:
            raise ValueError(
                f"agent case {index} must contain exactly {sorted(required_fields)}"
            )

        case_id = _required_string(raw_case["case_id"], "case_id", index)
        if case_id in seen_ids:
            raise ValueError(f"duplicate agent case_id '{case_id}'")
        seen_ids.add(case_id)

        policy_ids = _string_array(
            raw_case["expected_policy_ids"], "expected_policy_ids", index
        )
        required_terms = _string_array(
            raw_case["required_answer_terms"], "required_answer_terms", index
        )
        language = _required_string(
            raw_case["expected_language"], "expected_language", index
        ).lower()
        if language not in {"en", "th"}:
            raise ValueError(f"expected_language in case {index} must be 'en' or 'th'")

        should_abstain = raw_case["should_abstain"]
        if not isinstance(should_abstain, bool):
            raise ValueError(f"should_abstain in case {index} must be a boolean")
        if should_abstain and (policy_ids or required_terms):
            raise ValueError(
                f"abstention case {index} cannot require policy IDs or answer terms"
            )
        if not should_abstain and not policy_ids:
            raise ValueError(f"positive agent case {index} requires a policy ID")

        cases.append(
            AgentCase(
                case_id=case_id,
                employee_id=_required_string(
                    raw_case["employee_id"], "employee_id", index
                ),
                query=_required_string(raw_case["query"], "query", index),
                expected_policy_ids=frozenset(policy_ids),
                required_answer_terms=tuple(required_terms),
                expected_language=language,
                should_abstain=should_abstain,
            )
        )
    return tuple(cases)


def evaluate_agent_workflow(
    graph: AgentGraph,
    cases: Sequence[AgentCase],
    *,
    run_config_factory: RunConfigFactory | None = None,
) -> AgentEvaluation:
    """Score graph outputs against explicit evidence and answer contracts."""

    if not cases:
        raise ValueError("at least one agent evaluation case is required")

    results = tuple(
        _evaluate_case(graph, case, run_config_factory) for case in cases
    )
    positive_results = tuple(
        result
        for result, case in zip(results, cases, strict=True)
        if not case.should_abstain
    )
    negative_results = tuple(
        result
        for result, case in zip(results, cases, strict=True)
        if case.should_abstain
    )
    if not positive_results:
        raise ValueError("agent evaluation requires at least one positive case")

    metrics = AgentMetrics(
        evidence_accuracy=_rate(results, "evidence_match"),
        citation_accuracy=_rate(positive_results, "citation_match"),
        required_fact_accuracy=_rate(positive_results, "fact_match"),
        language_accuracy=_rate(positive_results, "language_match"),
        grounding_pass_rate=_rate(results, "grounding_valid"),
        abstention_accuracy=(
            _rate(negative_results, "abstention_match")
            if negative_results
            else None
        ),
        overall_pass_rate=_rate(results, "passed"),
        positive_cases=len(positive_results),
        negative_cases=len(negative_results),
    )
    return AgentEvaluation(metrics=metrics, cases=results)


def _evaluate_case(
    graph: AgentGraph,
    case: AgentCase,
    run_config_factory: RunConfigFactory | None,
) -> AgentCaseResult:
    try:
        config = run_config_factory(case) if run_config_factory else None
        output = graph.invoke(
            {"employee_id": case.employee_id, "user_query": case.query},
            config=config,
        )
        evidence = output.get("evidence")
        if not isinstance(evidence, list):
            raise TypeError("graph output evidence must be a list")
        retrieved_ids = tuple(
            str(item["policy_id"])
            for item in evidence
            if isinstance(item, Mapping) and item.get("policy_id")
        )
        answer = output.get("final_answer")
        if not isinstance(answer, str):
            raise TypeError("graph output final_answer must be a string")
        retrieval_query = output.get("retrieval_query")
        if not isinstance(retrieval_query, str) or not retrieval_query.strip():
            raise TypeError("graph output retrieval_query must be a non-empty string")

        cited_ids = tuple(sorted(set(_CITATION_PATTERN.findall(answer))))
        retrieved_set = set(retrieved_ids)
        cited_set = set(cited_ids)
        if case.should_abstain:
            evidence_match = not retrieved_ids
            citation_match = not cited_ids
            fact_match = True
            language_match = True
            abstention_match = answer == INSUFFICIENT_INFORMATION_RESPONSE
        else:
            evidence_match = case.expected_policy_ids <= retrieved_set
            citation_match = (
                case.expected_policy_ids <= cited_set <= retrieved_set
            )
            normalized_answer = answer.casefold()
            fact_match = all(
                term.casefold() in normalized_answer
                for term in case.required_answer_terms
            )
            language_match = _matches_language(answer, case.expected_language)
            abstention_match = answer != INSUFFICIENT_INFORMATION_RESPONSE

        grounding_valid = output.get("grounding_valid") is True
        passed = all(
            (
                evidence_match,
                citation_match,
                fact_match,
                language_match,
                grounding_valid,
                abstention_match,
            )
        )
        return AgentCaseResult(
            case_id=case.case_id,
            retrieval_query=retrieval_query.strip(),
            retrieved_policy_ids=retrieved_ids,
            cited_policy_ids=cited_ids,
            evidence_match=evidence_match,
            citation_match=citation_match,
            fact_match=fact_match,
            language_match=language_match,
            grounding_valid=grounding_valid,
            abstention_match=abstention_match,
            passed=passed,
            answer=answer,
        )
    except Exception as exc:  # Keep the remaining evaluation cases observable.
        return AgentCaseResult(
            case_id=case.case_id,
            retrieval_query="",
            retrieved_policy_ids=(),
            cited_policy_ids=(),
            evidence_match=False,
            citation_match=False,
            fact_match=False,
            language_match=False,
            grounding_valid=False,
            abstention_match=False,
            passed=False,
            answer="",
            error=f"{type(exc).__name__}: {exc}",
        )


def _matches_language(answer: str, expected_language: str) -> bool:
    contains_thai = _THAI_PATTERN.search(answer) is not None
    return contains_thai if expected_language == "th" else not contains_thai


def _rate(results: Sequence[AgentCaseResult], field_name: str) -> float:
    return sum(bool(getattr(result, field_name)) for result in results) / len(results)


def _string_array(value: object, field_name: str, case_index: int) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{field_name} in case {case_index} must be a string array")
    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} in case {case_index} contains duplicates")
    return normalized


def _required_string(value: object, field_name: str, case_index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} in case {case_index} must be a non-empty string"
        )
    return value.strip()
