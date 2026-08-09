"""Tests for deterministic full-workflow evaluation."""

from __future__ import annotations

import json

import pytest

from benefitwise.agent_evaluation import (
    AgentCase,
    evaluate_agent_workflow,
    load_agent_cases,
)
from benefitwise.agents import INSUFFICIENT_INFORMATION_RESPONSE


class ControlledGraph:
    def __init__(self, outputs):
        self.outputs = outputs
        self.invocations = []

    def invoke(self, input, config=None):
        self.invocations.append((input, config))
        output = self.outputs[input["user_query"]]
        if isinstance(output, Exception):
            raise output
        return output


def _case(
    case_id: str,
    query: str,
    *,
    should_abstain: bool = False,
    expected_language: str = "en",
) -> AgentCase:
    return AgentCase(
        case_id=case_id,
        employee_id="E001",
        query=query,
        expected_policy_ids=(
            frozenset() if should_abstain else frozenset({"MED-OPD"})
        ),
        required_answer_terms=() if should_abstain else ("14,250",),
        expected_language=expected_language,
        should_abstain=should_abstain,
    )


def test_evaluates_positive_and_abstention_contracts() -> None:
    graph = ControlledGraph(
        {
            "OPD?": {
                "retrieval_query": "outpatient limit",
                "evidence": [{"policy_id": "MED-OPD"}],
                "final_answer": "Limit THB 14,250.\n\n**Sources**\n- Policy section 4.4.1.1",
                "citation_policy_ids": ["MED-OPD"],
                "grounding_valid": True,
            },
            "Parking?": {
                "retrieval_query": "parking location",
                "evidence": [],
                "final_answer": INSUFFICIENT_INFORMATION_RESPONSE,
                "citation_policy_ids": [],
                "grounding_valid": True,
            },
        }
    )

    evaluation = evaluate_agent_workflow(
        graph,
        [_case("positive", "OPD?"), _case("negative", "Parking?", should_abstain=True)],
        run_config_factory=lambda case: {
            "metadata": {"case_id": case.case_id}
        },
    )

    assert all(result.passed for result in evaluation.cases)
    assert evaluation.metrics.overall_pass_rate == 1.0
    assert evaluation.metrics.abstention_accuracy == 1.0
    assert graph.invocations[0][1] == {"metadata": {"case_id": "positive"}}


def test_detects_wrong_citation_fact_language_and_grounding() -> None:
    graph = ControlledGraph(
        {
            "OPD?": {
                "retrieval_query": "outpatient limit",
                "evidence": [{"policy_id": "MED-OPD"}],
                "final_answer": "วงเงิน 99,999 บาท [OTHER-POLICY]",
                "grounding_valid": False,
            }
        }
    )

    result = evaluate_agent_workflow(graph, [_case("failed", "OPD?")]).cases[0]

    assert result.evidence_match is True
    assert result.citation_match is False
    assert result.fact_match is False
    assert result.language_match is False
    assert result.grounding_valid is False
    assert result.passed is False


def test_records_case_error_and_continues() -> None:
    graph = ControlledGraph(
        {
            "Broken?": RuntimeError("provider unavailable"),
            "OPD?": {
                "retrieval_query": "outpatient limit",
                "evidence": [{"policy_id": "MED-OPD"}],
                "final_answer": "Limit THB 14,250 [MED-OPD].",
                "grounding_valid": True,
            },
        }
    )

    evaluation = evaluate_agent_workflow(
        graph,
        [_case("broken", "Broken?"), _case("working", "OPD?")],
    )

    assert evaluation.cases[0].error == "RuntimeError: provider unavailable"
    assert evaluation.cases[1].passed is True
    assert evaluation.metrics.overall_pass_rate == 0.5


def test_loads_committed_case_schema(tmp_path) -> None:
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "thai-opd",
                    "employee_id": "E003",
                    "query": "วงเงิน OPD เท่าไร",
                    "expected_policy_ids": ["MED-OPD"],
                    "required_answer_terms": ["300"],
                    "expected_language": "th",
                    "should_abstain": False,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cases = load_agent_cases(dataset_path)

    assert cases[0].expected_policy_ids == frozenset({"MED-OPD"})
    assert cases[0].required_answer_terms == ("300",)
    assert cases[0].expected_language == "th"


@pytest.mark.parametrize(
    "case_update, message",
    [
        ({"expected_language": "jp"}, "expected_language"),
        ({"should_abstain": "yes"}, "should_abstain"),
        (
            {
                "should_abstain": True,
                "expected_policy_ids": ["MED-OPD"],
            },
            "cannot require",
        ),
        ({"expected_policy_ids": []}, "requires a policy ID"),
    ],
)
def test_rejects_invalid_case_contract(tmp_path, case_update, message) -> None:
    raw_case = {
        "case_id": "case-1",
        "employee_id": "E001",
        "query": "What is covered?",
        "expected_policy_ids": ["MED-OPD"],
        "required_answer_terms": [],
        "expected_language": "en",
        "should_abstain": False,
    }
    raw_case.update(case_update)
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(json.dumps([raw_case]), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_agent_cases(dataset_path)


def test_requires_at_least_one_positive_case() -> None:
    graph = ControlledGraph(
        {
            "Parking?": {
                "retrieval_query": "parking location",
                "evidence": [],
                "final_answer": INSUFFICIENT_INFORMATION_RESPONSE,
                "grounding_valid": True,
            }
        }
    )

    with pytest.raises(ValueError, match="positive"):
        evaluate_agent_workflow(
            graph,
            [_case("negative", "Parking?", should_abstain=True)],
        )
