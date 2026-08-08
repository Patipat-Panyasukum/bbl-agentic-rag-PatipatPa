"""SQLite persistence for trusted demo employee context."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from benefitwise.employee import EmployeeContext

DEFAULT_DATABASE_PATH = Path("data/employees.db")

DEMO_EMPLOYEES = (
    EmployeeContext("E001", "JL3", "TH", "DEMO", "General"),
    EmployeeContext("E002", "JL6", "TH", "DEMO", "General"),
    EmployeeContext("E003", "JL1", "TH", "DEMO", "Operations"),
)

_CREATE_EMPLOYEES_TABLE = """
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    job_level TEXT NOT NULL,
    country TEXT NOT NULL,
    company TEXT NOT NULL,
    employee_type TEXT NOT NULL
)
"""

_UPSERT_EMPLOYEE = """
INSERT INTO employees (
    employee_id,
    job_level,
    country,
    company,
    employee_type
)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(employee_id) DO UPDATE SET
    job_level = excluded.job_level,
    country = excluded.country,
    company = excluded.company,
    employee_type = excluded.employee_type
"""


class EmployeeNotFoundError(LookupError):
    """Raised when a canonical employee ID has no matching demo profile."""

    def __init__(self, employee_id: str) -> None:
        self.employee_id = employee_id
        super().__init__(f"Employee '{employee_id}' was not found.")


class EmployeeDatabaseNotInitializedError(RuntimeError):
    """Raised when employee lookup is attempted before database initialization."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        super().__init__(
            f"Employee database is not initialized at '{database_path}'."
        )


def initialize_employee_database(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    employees: Iterable[EmployeeContext] = DEMO_EMPLOYEES,
) -> Path:
    """Create the employee table and idempotently seed the supplied profiles."""

    resolved_path = Path(database_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    seed_rows = [
        (
            employee.employee_id,
            employee.job_level,
            employee.country,
            employee.company,
            employee.employee_type,
        )
        for employee in employees
    ]

    with sqlite3.connect(resolved_path) as connection:
        connection.execute(_CREATE_EMPLOYEES_TABLE)
        connection.executemany(_UPSERT_EMPLOYEE, seed_rows)

    return resolved_path


class SQLiteEmployeeRepository:
    """Resolve immutable employee context from a local SQLite database."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)

    def get_by_id(self, employee_id: str) -> EmployeeContext:
        """Return trusted context for an ID or raise a deterministic error."""

        normalized_id = _normalize_employee_id(employee_id)
        if not self.database_path.is_file():
            raise EmployeeDatabaseNotInitializedError(self.database_path)

        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute(
                    """
                    SELECT employee_id, job_level, country, company, employee_type
                    FROM employees
                    WHERE employee_id = ?
                    """,
                    (normalized_id,),
                ).fetchone()
        except sqlite3.OperationalError as error:
            if "no such table" not in str(error).lower():
                raise
            raise EmployeeDatabaseNotInitializedError(self.database_path) from error

        if row is None:
            raise EmployeeNotFoundError(normalized_id)

        return EmployeeContext(
            employee_id=row["employee_id"],
            job_level=row["job_level"],
            country=row["country"],
            company=row["company"],
            employee_type=row["employee_type"],
        )


def _normalize_employee_id(employee_id: str) -> str:
    if not isinstance(employee_id, str):
        raise TypeError("employee_id must be a string")

    normalized_id = employee_id.strip().upper()
    if not normalized_id:
        raise ValueError("employee_id must not be blank")
    return normalized_id
