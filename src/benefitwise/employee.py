"""Trusted employee context used by deterministic eligibility rules."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmployeeContext:
    """Employee metadata resolved before any LLM or agent is invoked."""

    employee_id: str
    job_level: str
    country: str
    company: str
    employee_type: str
