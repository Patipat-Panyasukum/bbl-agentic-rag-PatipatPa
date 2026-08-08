"""Parser for the explicit, reviewer-readable policy knowledge-base format."""

from __future__ import annotations

from pathlib import Path

from benefitwise.policy import PolicyChunk, PolicyEligibility

DEFAULT_KNOWLEDGE_BASE_PATH = Path("knowledge_base.txt")

_BLOCK_START = "[POLICY]"
_BLOCK_END = "[/POLICY]"
_CONTENT_KEY = "content"
_REQUIRED_METADATA = {
    "policy_id",
    "title",
    "countries",
    "companies",
    "employee_types",
    "min_job_level",
    "max_job_level",
}


class PolicyParseError(ValueError):
    """Raised when policy text cannot be converted into safe policy chunks."""

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        location = f" at line {line_number}" if line_number is not None else ""
        super().__init__(f"{message}{location}")


def load_policy_chunks(
    knowledge_base_path: str | Path = DEFAULT_KNOWLEDGE_BASE_PATH,
) -> tuple[PolicyChunk, ...]:
    """Load and parse policy chunks from the required local text file."""

    path = Path(knowledge_base_path)
    return parse_policy_chunks(path.read_text(encoding="utf-8"))


def parse_policy_chunks(text: str) -> tuple[PolicyChunk, ...]:
    """Parse all policy blocks and reject ambiguous or malformed metadata."""

    policies: list[PolicyChunk] = []
    policy_ids: set[str] = set()
    metadata: dict[str, str] | None = None
    content_lines: list[str] = []
    reading_content = False
    block_start_line: int | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()

        if metadata is None:
            if not line or line.startswith("#"):
                continue
            if line != _BLOCK_START:
                raise PolicyParseError(
                    f"Expected {_BLOCK_START}, found '{line}'", line_number
                )
            metadata = {}
            content_lines = []
            reading_content = False
            block_start_line = line_number
            continue

        if line == _BLOCK_END:
            policy = _build_policy(metadata, content_lines, block_start_line)
            if policy.policy_id in policy_ids:
                raise PolicyParseError(
                    f"Duplicate policy_id '{policy.policy_id}'", line_number
                )
            policies.append(policy)
            policy_ids.add(policy.policy_id)
            metadata = None
            reading_content = False
            block_start_line = None
            continue

        if reading_content:
            # Content is intentionally retained as raw evidence rather than
            # converted into LLM-authored summaries during ingestion.
            content_lines.append(raw_line.rstrip())
            continue

        if not line or line.startswith("#"):
            continue
        if "=" not in raw_line:
            raise PolicyParseError("Expected 'key = value' metadata", line_number)

        key, value = (part.strip() for part in raw_line.split("=", maxsplit=1))
        if key == _CONTENT_KEY:
            if value:
                content_lines.append(value)
            reading_content = True
            continue
        if key not in _REQUIRED_METADATA:
            raise PolicyParseError(f"Unknown policy field '{key}'", line_number)
        if key in metadata:
            raise PolicyParseError(f"Duplicate policy field '{key}'", line_number)
        metadata[key] = value

    if metadata is not None:
        raise PolicyParseError(f"Unclosed {_BLOCK_START} block", block_start_line)
    if not policies:
        raise PolicyParseError("Knowledge base contains no policy blocks")
    return tuple(policies)


def _build_policy(
    metadata: dict[str, str],
    content_lines: list[str],
    line_number: int | None,
) -> PolicyChunk:
    missing_fields = sorted(_REQUIRED_METADATA - metadata.keys())
    if missing_fields:
        raise PolicyParseError(
            f"Missing required fields: {', '.join(missing_fields)}", line_number
        )

    empty_fields = sorted(key for key, value in metadata.items() if not value)
    if empty_fields:
        raise PolicyParseError(
            f"Empty required fields: {', '.join(empty_fields)}", line_number
        )

    content = "\n".join(content_lines).strip()
    if not content:
        raise PolicyParseError("Policy content must not be empty", line_number)

    min_level = _parse_integer(metadata["min_job_level"], "min_job_level", line_number)
    max_level = _parse_integer(metadata["max_job_level"], "max_job_level", line_number)
    if min_level > max_level:
        raise PolicyParseError(
            "min_job_level must be less than or equal to max_job_level", line_number
        )

    return PolicyChunk(
        policy_id=metadata["policy_id"].strip(),
        title=metadata["title"].strip(),
        content=content,
        eligibility=PolicyEligibility(
            countries=_parse_allowed_values(metadata["countries"], "countries", line_number),
            companies=_parse_allowed_values(metadata["companies"], "companies", line_number),
            employee_types=_parse_allowed_values(
                metadata["employee_types"], "employee_types", line_number
            ),
            min_job_level=min_level,
            max_job_level=max_level,
        ),
    )


def _parse_allowed_values(
    value: str,
    field_name: str,
    line_number: int | None,
) -> frozenset[str]:
    values = frozenset(item.strip().upper() for item in value.split(",") if item.strip())
    if not values:
        raise PolicyParseError(f"{field_name} must contain at least one value", line_number)
    return values


def _parse_integer(value: str, field_name: str, line_number: int | None) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise PolicyParseError(f"{field_name} must be an integer", line_number) from error
    if parsed < 1:
        raise PolicyParseError(f"{field_name} must be at least 1", line_number)
    return parsed
