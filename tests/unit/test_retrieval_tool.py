"""Tests for the employee-bound LangChain retrieval tool."""

from pathlib import Path

from langchain_core.messages import ToolMessage

from benefitwise.employee import EmployeeContext
from benefitwise.policy_parser import load_policy_chunks
from benefitwise.retrieval import PolicyRetriever
from benefitwise.retrieval_tool import build_policy_retrieval_tool
from tests.fakes import KeywordEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _build_tool(employee: EmployeeContext):
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)
    return build_policy_retrieval_tool(retriever, employee)


def test_tool_schema_does_not_expose_employee_identity() -> None:
    tool = _build_tool(EmployeeContext("E001", "JL3", "TH", "DEMO", "General"))

    assert set(tool.args) == {"query", "top_k"}


def test_tool_returns_raw_employee_specific_evidence() -> None:
    tool = _build_tool(EmployeeContext("E001", "JL3", "TH", "DEMO", "General"))

    result = tool.invoke(
        {
            "name": tool.name,
            "args": {"query": "outpatient medical claim", "top_k": 1},
            "id": "tool-call-1",
            "type": "tool_call",
        }
    )

    assert isinstance(result, ToolMessage)
    assert "MED-OPD-GENERAL-JL2-8" in result.content
    assert "THB 14,250" in result.content
    assert "MED-OPD-OPERATIONS-JL1" not in result.content
    assert result.artifact[0]["policy_id"] == "MED-OPD-GENERAL-JL2-8"
    assert result.artifact[0]["applies_to_current_employee"] is True
    assert "search_terms" not in result.artifact[0]


def test_tool_answers_explicit_level_policy_and_marks_personal_applicability() -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)
    tool = build_policy_retrieval_tool(
        retriever,
        EmployeeContext("E001", "JL3", "TH", "DEMO", "General"),
        reference_query="What does the JL1 social security policy require?",
    )

    result = tool.invoke(
        {
            "name": tool.name,
            "args": {"query": "operations social security policy", "top_k": 3},
            "id": "tool-call-explicit-scope",
            "type": "tool_call",
        }
    )

    assert isinstance(result, ToolMessage)
    assert "MED-CLAIM-OPERATIONS-JL1" in result.content
    assert "Applies to current profile: no" in result.content
    assert any(
        item["policy_id"] == "MED-CLAIM-OPERATIONS-JL1"
        and item["applies_to_current_employee"] is False
        for item in result.artifact
    )


def test_tool_reports_no_evidence_for_irrelevant_query() -> None:
    tool = _build_tool(EmployeeContext("E003", "JL1", "TH", "DEMO", "Operations"))

    content = tool.invoke({"query": "employee parking location", "top_k": 3})

    assert content == (
        "No relevant policy evidence was found in the knowledge base."
    )


def test_tool_keeps_original_question_as_hidden_relevance_anchor() -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")
    retriever = PolicyRetriever(policies, KeywordEmbeddings(), min_similarity=0.1)
    tool = build_policy_retrieval_tool(
        retriever,
        EmployeeContext("E001", "JL3", "TH", "DEMO", "General"),
        reference_query="annual leave days",
    )

    content = tool.invoke({"query": "outpatient medical benefit", "top_k": 3})

    assert set(tool.args) == {"query", "top_k"}
    assert content == (
        "No relevant policy evidence was found in the knowledge base."
    )
