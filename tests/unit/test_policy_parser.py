"""Tests for policy parsing and deterministic metadata eligibility."""

from pathlib import Path

import pytest

from benefitwise.employee import EmployeeContext
from benefitwise.policy import filter_eligible_policies, parse_job_level
from benefitwise.policy_parser import PolicyParseError, load_policy_chunks, parse_policy_chunks

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_loads_expected_policy_ids_from_knowledge_base() -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")

    assert len(policies) == 12
    assert len({policy.policy_id for policy in policies}) == len(policies)
    assert "MED-OPD-JL1-4" in {policy.policy_id for policy in policies}
    assert "TRAVEL-INTL-JL8-10" in {policy.policy_id for policy in policies}


@pytest.mark.parametrize(
    ("employee", "expected_opd_policy"),
    [
        (EmployeeContext("E001", "JL3", "TH", "BBL", "Permanent"), "MED-OPD-JL1-4"),
        (EmployeeContext("E002", "JL6", "TH", "BBL", "Permanent"), "MED-OPD-JL5-7"),
        (EmployeeContext("E003", "JL9", "TH", "BBL", "Permanent"), "MED-OPD-JL8-10"),
    ],
)
def test_filters_opd_policy_by_job_level(employee, expected_opd_policy: str) -> None:
    policies = load_policy_chunks(PROJECT_ROOT / "knowledge_base.txt")

    eligible_ids = {
        policy.policy_id for policy in filter_eligible_policies(policies, employee)
    }
    opd_ids = {policy_id for policy_id in eligible_ids if policy_id.startswith("MED-OPD")}

    assert opd_ids == {expected_opd_policy}


@pytest.mark.parametrize(
    "employee",
    [
        EmployeeContext("X001", "JL6", "SG", "BBL", "Permanent"),
        EmployeeContext("X002", "JL6", "TH", "OTHER", "Permanent"),
        EmployeeContext("X003", "JL6", "TH", "BBL", "Contractor"),
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
    ("text", "message"),
    [
        ("", "contains no policy blocks"),
        ("[POLICY]\npolicy_id = P1", "Unclosed"),
        (
            """[POLICY]
policy_id = P1
title = Test
countries = TH
companies = BBL
employee_types = PERMANENT
min_job_level = 9
max_job_level = 3
content = Evidence
[/POLICY]""",
            "min_job_level",
        ),
    ],
)
def test_rejects_malformed_policy_blocks(text: str, message: str) -> None:
    with pytest.raises(PolicyParseError, match=message):
        parse_policy_chunks(text)
