"""Tests for the strict responsibilities of both BenefitWise agents."""

from pathlib import Path

import pytest

from benefitwise.agents import (
    INSUFFICIENT_INFORMATION_RESPONSE,
    AgentProtocolError,
    DataRetrieverAgent,
    ReportGeneratorAgent,
)
from benefitwise.employee import EmployeeContext
from benefitwise.policy_parser import load_policy_chunks
from benefitwise.retrieval import PolicyRetriever
from tests.fakes import FakeReportModel, FakeToolCallingModel, KeywordEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _retriever() -> PolicyRetriever:
    return PolicyRetriever(
        load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt"),
        KeywordEmbeddings(),
        min_similarity=0.1,
    )


def _employee() -> EmployeeContext:
    return EmployeeContext("E001", "JL3", "TH", "DEMO", "General")


def _opd_evidence() -> list[dict[str, object]]:
    return [
        item.as_dict()
        for item in _retriever().retrieve("outpatient medical", _employee(), top_k=1)
    ]


def _out_of_profile_policy_evidence() -> list[dict[str, object]]:
    evidence = _retriever().retrieve_policy_information(
        "operations social security policy",
        _employee(),
    )
    return [
        item.as_dict()
        for item in evidence
        if item.policy_id == "MED-CLAIM-OPERATIONS-JL1"
    ]


def test_data_retriever_must_call_employee_bound_tool() -> None:
    model = FakeToolCallingModel("clinic visit allowance")
    agent = DataRetrieverAgent(model, _retriever(), top_k=2)

    tool_call = agent.create_tool_call("What can I claim at a clinic?", _employee())

    assert model.tool_choice == "retrieve_benefit_policies"
    assert set(model.bound_tools[0].args) == {"query", "top_k"}
    assert tool_call["args"] == {"query": "clinic visit allowance", "top_k": 2}
    assert model.invocations


def test_data_retriever_rejects_direct_answer_without_tool_call() -> None:
    model = FakeToolCallingModel(tool_calls=[])
    agent = DataRetrieverAgent(model, _retriever())

    with pytest.raises(AgentProtocolError, match="exactly one tool call"):
        agent.create_tool_call("How much is OPD?", _employee())


def test_data_retriever_rejects_blank_user_question_before_model_call() -> None:
    model = FakeToolCallingModel()
    agent = DataRetrieverAgent(model, _retriever())

    with pytest.raises(ValueError, match="must not be blank"):
        agent.create_tool_call("   ", _employee())

    assert model.invocations == []


def test_data_retriever_rejects_blank_model_search_query() -> None:
    model = FakeToolCallingModel("   ")
    agent = DataRetrieverAgent(model, _retriever())

    with pytest.raises(AgentProtocolError, match="blank search query"):
        agent.create_tool_call("How much is OPD?", _employee())


def test_report_generator_returns_cited_supported_answer() -> None:
    model = FakeReportModel(
        "You may claim up to THB 14,250 per year [MED-OPD-GENERAL-JL2-8]."
    )
    agent = ReportGeneratorAgent(model)

    result = agent.generate("What is my OPD limit?", _employee(), _opd_evidence())

    assert result.grounding_valid is True
    assert "THB 14,250" in result.answer
    assert "MED-OPD-GENERAL-JL2-8" not in result.answer
    assert "**Sources**" in result.answer
    assert result.citation_policy_ids == ("MED-OPD-GENERAL-JL2-8",)
    assert len(model.invocations) == 1
    assert "Required answer language: English" in model.invocations[0][-1].content


def test_report_generator_pins_thai_language_from_question() -> None:
    model = FakeReportModel(
        "เบิกได้ไม่เกิน THB 14,250 ต่อปี "
        "[MED-OPD-GENERAL-JL2-8]."
    )
    agent = ReportGeneratorAgent(model)

    result = agent.generate(
        "วงเงิน OPD เท่าไร",
        _employee(),
        _opd_evidence(),
    )

    assert result.grounding_valid is True
    assert "MED-OPD-GENERAL-JL2-8" not in result.answer
    assert "**แหล่งอ้างอิง**" in result.answer
    assert result.citation_policy_ids == ("MED-OPD-GENERAL-JL2-8",)
    assert "Required answer language: Thai" in model.invocations[0][-1].content


def test_report_generator_receives_policy_first_and_profile_applicability_contract() -> None:
    model = FakeReportModel(
        "The policy requires social security first [MED-CLAIM-OPERATIONS-JL1]."
    )
    agent = ReportGeneratorAgent(model)

    result = agent.generate(
        "What does the JL1 social security policy require?",
        _employee(),
        _out_of_profile_policy_evidence(),
    )

    assert result.grounding_valid is True
    assert "does not apply" in result.answer
    assert "E001 (JL3)" in result.answer
    assert "MED-CLAIM-OPERATIONS-JL1" not in result.answer
    assert result.citation_policy_ids == ("MED-CLAIM-OPERATIONS-JL1",)
    system_prompt = model.invocations[0][0].content
    request = model.invocations[0][-1].content
    assert "Answer the policy question first" in system_prompt
    assert "Applies to current profile: no" in request


@pytest.mark.parametrize(
    "unsupported_answer",
    [
        "You may claim THB 99,999 [MED-OPD-GENERAL-JL2-8].",
        "You may claim THB 14,250 [UNKNOWN-POLICY].",
        "You may claim THB 14,250 per year.",
    ],
)
def test_report_generator_fails_closed_on_unsupported_answer(
    unsupported_answer: str,
) -> None:
    agent = ReportGeneratorAgent(FakeReportModel(unsupported_answer))

    result = agent.generate("What is my OPD limit?", _employee(), _opd_evidence())

    assert result.grounding_valid is False
    assert result.answer == INSUFFICIENT_INFORMATION_RESPONSE


def test_report_generator_does_not_call_model_without_evidence() -> None:
    model = FakeReportModel("This response must never be used")
    agent = ReportGeneratorAgent(model)

    result = agent.generate("Where can I park?", _employee(), [])

    assert result.answer == INSUFFICIENT_INFORMATION_RESPONSE
    assert result.grounding_valid is True
    assert result.citation_policy_ids == ()
    assert model.invocations == []
