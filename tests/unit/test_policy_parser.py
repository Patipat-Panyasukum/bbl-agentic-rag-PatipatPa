"""Tests for clean policy text joined with deterministic sidecar metadata."""

import json
from pathlib import Path

import pytest

from benefitwise.employee import EmployeeContext
from benefitwise.policy import filter_eligible_policies, parse_job_level
from benefitwise.policy_parser import PolicyParseError, load_policy_chunks, parse_policy_chunks

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _metadata(
    *,
    section_id: str = "2.1",
    min_job_level: int = 2,
    max_job_level: int = 8,
) -> str:
    return json.dumps(
        {
            "version": 1,
            "chunks": [
                {
                    "policy_id": "TEST-POLICY",
                    "section_id": section_id,
                    "search_terms": ["test policy"],
                    "eligibility": {
                        "countries": ["TH"],
                        "companies": ["DEMO"],
                        "employee_types": ["GENERAL"],
                        "min_job_level": min_job_level,
                        "max_job_level": max_job_level,
                    },
                }
            ],
        }
    )


def test_loads_expected_policy_ids_from_text_and_sidecar() -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")

    assert len(policies) == 12
    assert len({policy.policy_id for policy in policies}) == len(policies)
    assert "MED-OPD-GENERAL-JL2-8" in {policy.policy_id for policy in policies}
    assert "MED-OPD-OPERATIONS-JL1" in {policy.policy_id for policy in policies}


def test_uses_source_section_as_raw_evidence() -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")
    opd = next(
        policy for policy in policies if policy.policy_id == "MED-OPD-GENERAL-JL2-8"
    )

    assert opd.title.startswith("4.4.1.1 คนไข้นอก")
    assert "14,250 บาทต่อปี" in opd.content
    assert "min_job_level" not in opd.content
    assert "outpatient medical benefit" in opd.search_terms
    assert "ค่ารักษาพยาบาลผู้ป่วยนอก เบิกได้เท่าไร" in opd.search_terms


@pytest.mark.parametrize(
    ("employee", "expected_opd_policy"),
    [
        (
            EmployeeContext("E001", "JL3", "TH", "DEMO", "General"),
            "MED-OPD-GENERAL-JL2-8",
        ),
        (
            EmployeeContext("E002", "JL6", "TH", "DEMO", "General"),
            "MED-OPD-GENERAL-JL2-8",
        ),
        (
            EmployeeContext("E003", "JL1", "TH", "DEMO", "Operations"),
            "MED-OPD-OPERATIONS-JL1",
        ),
    ],
)
def test_filters_opd_policy_by_sidecar_metadata(
    employee,
    expected_opd_policy: str,
) -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")

    eligible_ids = {
        policy.policy_id for policy in filter_eligible_policies(policies, employee)
    }
    opd_ids = {policy_id for policy_id in eligible_ids if policy_id.startswith("MED-OPD")}

    assert opd_ids == {expected_opd_policy}


@pytest.mark.parametrize(
    "employee",
    [
        EmployeeContext("X001", "JL6", "SG", "DEMO", "General"),
        EmployeeContext("X002", "JL6", "TH", "OTHER", "General"),
        EmployeeContext("X003", "JL6", "TH", "DEMO", "Contractor"),
    ],
)
def test_filters_policies_by_all_employee_metadata(employee) -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")

    assert filter_eligible_policies(policies, employee) == ()


@pytest.mark.parametrize(("job_level", "expected"), [("JL1", 1), ("jl6", 6), (" JL10 ", 10)])
def test_parse_job_level(job_level: str, expected: int) -> None:
    assert parse_job_level(job_level) == expected


@pytest.mark.parametrize("job_level", ["", "L6", "JL0", "JLX"])
def test_parse_job_level_rejects_invalid_codes(job_level: str) -> None:
    with pytest.raises(ValueError, match="Invalid job level"):
        parse_job_level(job_level)


@pytest.mark.parametrize(
    ("policy_text", "metadata_text", "message"),
    [
        ("", _metadata(), "no numbered policy sections"),
        ("2.1 Test section\nEvidence", "{", "valid JSON"),
        (
            "2.1 Test section\nEvidence",
            _metadata(section_id="9.9"),
            "unknown policy section",
        ),
        (
            "2.1 Test section\nEvidence",
            _metadata(min_job_level=9, max_job_level=3),
            "min_job_level",
        ),
    ],
)
def test_rejects_malformed_source_or_metadata(
    policy_text: str,
    metadata_text: str,
    message: str,
) -> None:
    with pytest.raises(PolicyParseError, match=message):
        parse_policy_chunks(policy_text, metadata_text)


def test_knowledge_base_contains_policy_only() -> None:
    text = (PROJECT_ROOT / "knowledge_base.txt").read_text(encoding="utf-8")

    for marker in (
        "[POLICY]",
        "[/POLICY]",
        "min_job_level",
        "max_job_level",
        "companies =",
        "employee_types =",
        "<!--",
        "with ID",
        "signature:",
        "อนุมัติโดย",
        "~~",
    ):
        assert marker not in text


def test_sidecar_contains_retrieval_metadata() -> None:
    metadata = json.loads(
        (PROJECT_ROOT / "policy_metadata.json").read_text(encoding="utf-8")
    )

    assert metadata["version"] == 1
    assert len(metadata["chunks"]) == 12
    assert metadata["chunks"][0]["search_terms"]
    assert metadata["chunks"][0]["eligibility"]["min_job_level"] == 2
