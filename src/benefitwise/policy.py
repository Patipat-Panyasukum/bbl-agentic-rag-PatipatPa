"""Policy domain types and deterministic eligibility rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

from benefitwise.employee import EmployeeContext

_JOB_LEVEL_PATTERN = re.compile(r"^JL(?P<level>[1-9][0-9]*)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PolicyEligibility:
    """Metadata rules that determine policy applicability to an employee."""

    countries: frozenset[str]
    companies: frozenset[str]
    employee_types: frozenset[str]
    min_job_level: int
    max_job_level: int

    def allows(self, employee: EmployeeContext) -> bool:
        """Apply access rules without involving an LLM or similarity score."""

        job_level = parse_job_level(employee.job_level)
        return (
            _allows_value(self.countries, employee.country)
            and _allows_value(self.companies, employee.company)
            and _allows_value(self.employee_types, employee.employee_type)
            and self.min_job_level <= job_level <= self.max_job_level
        )

    def as_dict(self) -> dict[str, object]:
        """Return stable, JSON-compatible metadata for tool evidence."""

        return {
            "countries": sorted(self.countries),
            "companies": sorted(self.companies),
            "employee_types": sorted(self.employee_types),
            "min_job_level": self.min_job_level,
            "max_job_level": self.max_job_level,
        }


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    """A single retrievable policy and its deterministic access metadata."""

    policy_id: str
    title: str
    content: str
    eligibility: PolicyEligibility
    search_terms: tuple[str, ...] = ()

    @property
    def searchable_text(self) -> str:
        """Text presented to the embedding model after candidate selection."""

        retrieval_hints = "\n".join(self.search_terms)
        return "\n".join(part for part in (self.title, self.content, retrieval_hints) if part)


def parse_job_level(job_level: str) -> int:
    """Convert a canonical code such as JL6 into its numeric level."""

    if not isinstance(job_level, str):
        raise TypeError("job_level must be a string")

    match = _JOB_LEVEL_PATTERN.fullmatch(job_level.strip())
    if match is None:
        raise ValueError(f"Invalid job level '{job_level}'; expected JL followed by digits")
    return int(match.group("level"))


def filter_eligible_policies(
    policies: tuple[PolicyChunk, ...] | list[PolicyChunk],
    employee: EmployeeContext,
) -> tuple[PolicyChunk, ...]:
    """Return policies applicable to a trusted employee for personal retrieval."""

    return tuple(policy for policy in policies if policy.eligibility.allows(employee))


def _allows_value(allowed_values: frozenset[str], actual_value: str) -> bool:
    normalized_value = actual_value.strip().upper()
    return "*" in allowed_values or normalized_value in allowed_values
