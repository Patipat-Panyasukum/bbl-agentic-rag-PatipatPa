"""Run one BenefitWise employee question through the complete LangGraph."""

from __future__ import annotations

import argparse

from benefitwise.application import create_default_graph
from benefitwise.observability import build_run_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--employee-id", required=True, help="Demo employee ID")
    parser.add_argument("--query", required=True, help="Employee benefit question")
    parser.add_argument(
        "--show-evidence",
        action="store_true",
        help="Print retrieved policy IDs and similarity scores",
    )
    args = parser.parse_args()

    graph = create_default_graph()
    result = graph.invoke(
        {"employee_id": args.employee_id, "user_query": args.query},
        config=build_run_config(source="cli", employee_id=args.employee_id),
    )

    context = result["employee_context"]
    print(f"Employee: {context.employee_id} ({context.job_level})")
    if args.show_evidence:
        for item in result["evidence"]:
            print(
                f"Evidence: {item['policy_id']} "
                f"(score={float(item['similarity_score']):.4f})"
            )
    print()
    print(result["final_answer"])


if __name__ == "__main__":
    main()
