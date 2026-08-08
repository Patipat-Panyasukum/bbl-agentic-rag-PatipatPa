"""Run the committed retrieval evaluation with OpenAI embeddings."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from benefitwise.embeddings import DEFAULT_EMBEDDING_MODEL, OpenAIEmbeddingProvider
from benefitwise.employee_repository import (
    DEFAULT_DATABASE_PATH,
    SQLiteEmployeeRepository,
    initialize_employee_database,
)
from benefitwise.evaluation import DEFAULT_EVALUATION_PATH, evaluate_retrieval, load_retrieval_cases
from benefitwise.policy_parser import (
    DEFAULT_KNOWLEDGE_BASE_PATH,
    DEFAULT_POLICY_METADATA_PATH,
    load_policy_chunks,
)
from benefitwise.retrieval import PolicyRetriever


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_EVALUATION_PATH)
    parser.add_argument("--knowledge-base", type=Path, default=DEFAULT_KNOWLEDGE_BASE_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_POLICY_METADATA_PATH)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-similarity", type=float, default=0.26)
    args = parser.parse_args()

    initialize_employee_database(args.database)
    employee_repository = SQLiteEmployeeRepository(args.database)
    policies = load_policy_chunks(args.knowledge_base, args.metadata)
    retriever = PolicyRetriever(
        policies,
        OpenAIEmbeddingProvider(
            args.model,
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        ),
        min_similarity=args.min_similarity,
    )
    evaluation = evaluate_retrieval(
        retriever,
        employee_repository.get_by_id,
        load_retrieval_cases(args.dataset),
        top_k=args.top_k,
    )

    for case in evaluation.cases:
        status = "PASS" if case.passed else "FAIL"
        expected = ", ".join(case.expected_policy_ids) or "<no evidence>"
        retrieved = ", ".join(case.retrieved_policy_ids) or "<no evidence>"
        print(f"{status} {case.case_id}: expected={expected}; retrieved={retrieved}")

    metrics = evaluation.metrics
    print()
    print(f"Hit@1: {metrics.hit_at_1:.3f}")
    print(f"Hit@{metrics.top_k}: {metrics.hit_at_k:.3f}")
    print(f"MRR: {metrics.mrr:.3f}")
    if metrics.no_evidence_accuracy is not None:
        print(f"No-evidence accuracy: {metrics.no_evidence_accuracy:.3f}")

    failed_case_count = sum(not case.passed for case in evaluation.cases)
    if failed_case_count:
        raise SystemExit(f"{failed_case_count} retrieval case(s) failed")


if __name__ == "__main__":
    main()
