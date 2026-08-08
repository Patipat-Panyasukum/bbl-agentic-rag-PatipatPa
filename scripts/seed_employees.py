"""Create or refresh the local fictional employee database."""

from __future__ import annotations

import argparse
from pathlib import Path

from benefitwise.employee_repository import (
    DEFAULT_DATABASE_PATH,
    DEMO_EMPLOYEES,
    initialize_employee_database,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help=f"SQLite output path (default: {DEFAULT_DATABASE_PATH})",
    )
    args = parser.parse_args()

    database_path = initialize_employee_database(args.database)
    print(f"Seeded {len(DEMO_EMPLOYEES)} employees at {database_path}")


if __name__ == "__main__":
    main()
