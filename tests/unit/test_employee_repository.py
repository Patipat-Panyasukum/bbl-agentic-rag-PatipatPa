"""Tests for deterministic employee database initialization and lookup."""

import sqlite3

import pytest

from benefitwise.employee import EmployeeContext
from benefitwise.employee_repository import (
    DEMO_EMPLOYEES,
    EmployeeDatabaseNotInitializedError,
    EmployeeNotFoundError,
    SQLiteEmployeeRepository,
    initialize_employee_database,
)


@pytest.fixture
def repository(tmp_path) -> SQLiteEmployeeRepository:
    database_path = initialize_employee_database(tmp_path / "employees.db")
    return SQLiteEmployeeRepository(database_path)


@pytest.mark.parametrize("expected", DEMO_EMPLOYEES)
def test_get_by_id_returns_each_demo_employee(
    repository: SQLiteEmployeeRepository,
    expected: EmployeeContext,
) -> None:
    assert repository.get_by_id(expected.employee_id) == expected


def test_get_by_id_normalizes_whitespace_and_case(
    repository: SQLiteEmployeeRepository,
) -> None:
    assert repository.get_by_id("  e002 ").employee_id == "E002"


def test_get_by_id_raises_explicit_error_for_unknown_employee(
    repository: SQLiteEmployeeRepository,
) -> None:
    with pytest.raises(EmployeeNotFoundError, match="E999") as raised:
        repository.get_by_id("E999")

    assert raised.value.employee_id == "E999"


@pytest.mark.parametrize("employee_id", ["", "   "])
def test_get_by_id_rejects_blank_employee_id(
    repository: SQLiteEmployeeRepository,
    employee_id: str,
) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        repository.get_by_id(employee_id)


def test_lookup_does_not_create_an_uninitialized_database(tmp_path) -> None:
    database_path = tmp_path / "missing" / "employees.db"
    repository = SQLiteEmployeeRepository(database_path)

    with pytest.raises(EmployeeDatabaseNotInitializedError):
        repository.get_by_id("E001")

    assert not database_path.exists()


def test_initialization_is_repeatable_without_duplicate_rows(tmp_path) -> None:
    database_path = tmp_path / "nested" / "employees.db"

    initialize_employee_database(database_path)
    initialize_employee_database(database_path)

    with sqlite3.connect(database_path) as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM employees").fetchone()[0]

    assert row_count == len(DEMO_EMPLOYEES)
