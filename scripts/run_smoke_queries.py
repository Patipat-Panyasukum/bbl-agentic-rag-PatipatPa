"""Run representative API-backed E2E queries and check expected evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benefitwise.agents import INSUFFICIENT_INFORMATION_RESPONSE
from benefitwise.application import create_default_graph
from benefitwise.observability import build_run_config

DEFAULT_CASES_PATH = Path("examples/demo_queries.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument(
        "--limit",
        type=int,
        help="Run only the first N cases to control API cost during development",
    )
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be at least 1")
        cases = cases[: args.limit]

    graph = create_default_graph()
    failed = 0
    for case in cases:
        result = graph.invoke(
            {"employee_id": case["employee_id"], "user_query": case["query"]},
            config=build_run_config(
                source="smoke",
                employee_id=case["employee_id"],
                case_id=case["case_id"],
            ),
        )
        retrieved_ids = [item["policy_id"] for item in result["evidence"]]
        expected_policy_id = case["expected_policy_id"]
        if expected_policy_id is None:
            passed = not retrieved_ids and result["final_answer"] == (
                INSUFFICIENT_INFORMATION_RESPONSE
            )
        else:
            passed = (
                expected_policy_id in retrieved_ids
                and f"[{expected_policy_id}]" in result["final_answer"]
                and result["grounding_valid"]
            )

        status = "PASS" if passed else "FAIL"
        print(
            f"{status} {case['case_id']}: employee={case['employee_id']} "
            f"evidence={retrieved_ids or '<none>'}"
        )
        print(f"  {result['final_answer']}")
        failed += not passed

    if failed:
        raise SystemExit(f"{failed} smoke case(s) failed")


if __name__ == "__main__":
    main()
