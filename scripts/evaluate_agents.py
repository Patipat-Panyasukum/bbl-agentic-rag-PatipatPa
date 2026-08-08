"""Run the committed API-backed full-workflow evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from benefitwise.agent_evaluation import (
    DEFAULT_AGENT_EVALUATION_PATH,
    AgentCase,
    evaluate_agent_workflow,
    load_agent_cases,
)
from benefitwise.application import create_default_graph
from benefitwise.observability import build_run_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_AGENT_EVALUATION_PATH)
    parser.add_argument(
        "--limit",
        type=int,
        help="Run only the first N cases to control API cost during development",
    )
    args = parser.parse_args()

    cases = load_agent_cases(args.dataset)
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be at least 1")
        cases = cases[: args.limit]

    graph = create_default_graph()
    evaluation = evaluate_agent_workflow(
        graph,
        cases,
        run_config_factory=_evaluation_run_config,
    )

    for case in evaluation.cases:
        status = "PASS" if case.passed else "FAIL"
        evidence = ", ".join(case.retrieved_policy_ids) or "<none>"
        citations = ", ".join(case.cited_policy_ids) or "<none>"
        print(
            f"{status} {case.case_id}: evidence={evidence}; citations={citations}"
        )
        if case.retrieval_query:
            print(f"  retrieval_query={case.retrieval_query}")
        if case.error:
            print(f"  error={case.error}")
        else:
            print(f"  {case.answer}")

    metrics = evaluation.metrics
    print()
    print(f"Evidence accuracy: {metrics.evidence_accuracy:.3f}")
    print(f"Citation accuracy: {metrics.citation_accuracy:.3f}")
    print(f"Required-fact accuracy: {metrics.required_fact_accuracy:.3f}")
    print(f"Language accuracy: {metrics.language_accuracy:.3f}")
    print(f"Grounding pass rate: {metrics.grounding_pass_rate:.3f}")
    if metrics.abstention_accuracy is not None:
        print(f"Abstention accuracy: {metrics.abstention_accuracy:.3f}")
    print(f"Overall pass rate: {metrics.overall_pass_rate:.3f}")

    failed_case_count = sum(not case.passed for case in evaluation.cases)
    if failed_case_count:
        raise SystemExit(f"{failed_case_count} agent evaluation case(s) failed")


def _evaluation_run_config(case: AgentCase):
    return build_run_config(
        source="evaluation",
        employee_id=case.employee_id,
        case_id=case.case_id,
    )


if __name__ == "__main__":
    main()
