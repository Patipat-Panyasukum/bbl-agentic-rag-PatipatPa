"""Integration tests for the complete deterministic-to-two-agent graph."""

from pathlib import Path

import pytest

from benefitwise.agents import INSUFFICIENT_INFORMATION_RESPONSE
from benefitwise.employee_repository import (
    EmployeeNotFoundError,
    SQLiteEmployeeRepository,
    initialize_employee_database,
)
from benefitwise.graph import build_benefit_graph
from benefitwise.policy_parser import load_policy_chunks
from benefitwise.retrieval import PolicyRetriever
from tests.fakes import EvidenceEchoReportModel, FakeToolCallingModel, KeywordEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _build_graph(tmp_path, search_query: str, report_model):
    database_path = initialize_employee_database(tmp_path / "employees.db")
    repository = SQLiteEmployeeRepository(database_path)
    retriever = PolicyRetriever(
        load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt"),
        KeywordEmbeddings(),
        min_similarity=0.1,
    )
    retriever_model = FakeToolCallingModel(search_query)
    graph = build_benefit_graph(
        repository,
        retriever,
        retriever_model,
        report_model,
        top_k=1,
    )
    return graph, retriever_model


@pytest.mark.parametrize(
    ("employee_id", "expected_policy", "expected_amount"),
    [
        ("E001", "MED-OPD-GENERAL-JL2-8", "THB 14,250"),
        ("E002", "MED-OPD-GENERAL-JL2-8", "THB 14,250"),
        ("E003", "MED-OPD-OPERATIONS-JL1", "THB 300"),
    ],
)
def test_same_question_flows_through_graph_with_personalized_evidence(
    tmp_path,
    employee_id: str,
    expected_policy: str,
    expected_amount: str,
) -> None:
    report_model = EvidenceEchoReportModel()
    graph, retriever_model = _build_graph(
        tmp_path, "outpatient medical expenses", report_model
    )

    result = graph.invoke(
        {
            "employee_id": employee_id,
            "user_query": "How much can I claim for outpatient medical expenses?",
        }
    )

    assert result["employee_context"].employee_id == employee_id
    assert result["retrieval_query"] == "outpatient medical expenses"
    assert result["evidence"][0]["policy_id"] == expected_policy
    assert expected_amount in result["final_answer"]
    assert result["grounding_valid"] is True
    assert len(retriever_model.invocations) == 1
    assert len(report_model.invocations) == 1


def test_graph_stops_before_agents_for_unknown_employee(tmp_path) -> None:
    report_model = EvidenceEchoReportModel()
    graph, retriever_model = _build_graph(
        tmp_path, "outpatient medical expenses", report_model
    )

    with pytest.raises(EmployeeNotFoundError):
        graph.invoke({"employee_id": "E999", "user_query": "What is my OPD limit?"})

    assert retriever_model.invocations == []
    assert report_model.invocations == []


def test_graph_returns_grounded_abstention_for_unsupported_query(tmp_path) -> None:
    report_model = EvidenceEchoReportModel()
    graph, _ = _build_graph(tmp_path, "employee parking location", report_model)

    result = graph.invoke(
        {"employee_id": "E003", "user_query": "Where can I park my car?"}
    )

    assert result["evidence"] == []
    assert result["final_answer"] == INSUFFICIENT_INFORMATION_RESPONSE
    assert result["grounding_valid"] is True
    assert report_model.invocations == []


def test_graph_anchors_agent_query_to_original_question(tmp_path) -> None:
    report_model = EvidenceEchoReportModel()
    graph, _ = _build_graph(tmp_path, "outpatient medical expenses", report_model)

    result = graph.invoke(
        {"employee_id": "E001", "user_query": "How many annual leave days do I have?"}
    )

    assert result["retrieval_query"] == "outpatient medical expenses"
    assert result["evidence"] == []
    assert result["final_answer"] == INSUFFICIENT_INFORMATION_RESPONSE
    assert result["grounding_valid"] is True
    assert report_model.invocations == []


def test_graph_exposes_expected_sequential_nodes(tmp_path) -> None:
    graph, _ = _build_graph(
        tmp_path, "annual leave", EvidenceEchoReportModel()
    )

    node_names = set(graph.get_graph().nodes)

    assert {
        "resolve_employee",
        "data_retriever_agent",
        "retrieval_tool",
        "report_generator_agent",
    } <= node_names
