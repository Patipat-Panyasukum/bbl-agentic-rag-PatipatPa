"""Join clean policy sections with deterministic retrieval metadata."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benefitwise.policy import PolicyChunk, PolicyEligibility

DEFAULT_KNOWLEDGE_BASE_PATH = Path("knowledge_base.txt")
DEFAULT_POLICY_METADATA_PATH = Path("policy_metadata.json")

_SECTION_HEADING = re.compile(
    r"^(?P<section_id>[1-9][0-9]*(?:\.[0-9]+)+)\s+(?P<title>\S.*)$"
)
_ANY_NUMBERED_HEADING = re.compile(r"^[1-9][0-9]*(?:\.[0-9]+)*\.?\s+\S")
_CHUNK_FIELDS = {"policy_id", "section_id", "search_terms", "eligibility"}
_ELIGIBILITY_FIELDS = {
    "countries",
    "companies",
    "employee_types",
    "min_job_level",
    "max_job_level",
}


@dataclass(frozen=True, slots=True)
class _PolicySection:
    section_id: str
    title: str
    content: str


class PolicyParseError(ValueError):
    """Raised when source text and metadata cannot form safe policy chunks."""

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        location = f" at line {line_number}" if line_number is not None else ""
        super().__init__(f"{message}{location}")


def load_policy_chunks(
    knowledge_base_path: str | Path = DEFAULT_KNOWLEDGE_BASE_PATH,
    metadata_path: str | Path | None = None,
) -> tuple[PolicyChunk, ...]:
    """Load clean policy text and its sibling retrieval-metadata sidecar."""

    source_path = Path(knowledge_base_path)
    resolved_metadata_path = (
        Path(metadata_path)
        if metadata_path is not None
        else source_path.with_name(DEFAULT_POLICY_METADATA_PATH.name)
    )
    return parse_policy_chunks(
        source_path.read_text(encoding="utf-8"),
        resolved_metadata_path.read_text(encoding="utf-8"),
    )


def parse_policy_chunks(
    policy_text: str,
    metadata_text: str,
) -> tuple[PolicyChunk, ...]:
    """Attach validated sidecar rules to numbered sections in policy text."""

    sections = _parse_policy_sections(policy_text)
    metadata_chunks = _parse_metadata(metadata_text)
    policies: list[PolicyChunk] = []
    policy_ids: set[str] = set()

    for item in metadata_chunks:
        policy_id = _required_string(item, "policy_id")
        section_id = _required_string(item, "section_id")
        if policy_id in policy_ids:
            raise PolicyParseError(f"Duplicate policy_id '{policy_id}'")
        if section_id not in sections:
            raise PolicyParseError(
                f"Metadata references unknown policy section '{section_id}'"
            )

        section = sections[section_id]
        policies.append(
            PolicyChunk(
                policy_id=policy_id,
                title=f"{section.section_id} {section.title}",
                content=section.content,
                eligibility=_parse_eligibility(item["eligibility"], policy_id),
                search_terms=_required_string_tuple(item, "search_terms", policy_id),
            )
        )
        policy_ids.add(policy_id)

    return tuple(policies)


def _parse_policy_sections(text: str) -> dict[str, _PolicySection]:
    sections: dict[str, _PolicySection] = {}
    current_id: str | None = None
    current_title = ""
    content_lines: list[str] = []

    def store_current() -> None:
        nonlocal current_id, current_title, content_lines
        if current_id is None:
            return
        content = "\n".join(content_lines).strip()
        # Container headings such as 4.4.1 may be followed immediately by
        # smaller numbered clauses. Only sections with source text are chunks.
        if content:
            sections[current_id] = _PolicySection(current_id, current_title, content)
        current_id = None
        current_title = ""
        content_lines = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        section_match = _SECTION_HEADING.fullmatch(line)
        if section_match is not None:
            store_current()
            section_id = section_match.group("section_id")
            if section_id in sections:
                raise PolicyParseError(
                    f"Duplicate policy section '{section_id}'", line_number
                )
            current_id = section_id
            current_title = section_match.group("title")
            continue

        # A top-level numbered heading closes the preceding subsection but is
        # not itself a retrieval chunk. This keeps source formatting natural.
        if _ANY_NUMBERED_HEADING.match(line):
            store_current()
            continue
        if current_id is not None:
            content_lines.append(raw_line.rstrip())

    store_current()
    if not sections:
        raise PolicyParseError("Knowledge base contains no numbered policy sections")
    return sections


def _parse_metadata(metadata_text: str) -> list[dict[str, Any]]:
    try:
        document = json.loads(metadata_text)
    except json.JSONDecodeError as error:
        raise PolicyParseError(
            f"Policy metadata must be valid JSON: {error.msg}", error.lineno
        ) from error

    if not isinstance(document, dict):
        raise PolicyParseError("Policy metadata root must be an object")
    if set(document) != {"version", "chunks"}:
        raise PolicyParseError("Policy metadata requires only version and chunks")
    if document["version"] != 1:
        raise PolicyParseError("Unsupported policy metadata version")

    chunks = document["chunks"]
    if not isinstance(chunks, list) or not chunks:
        raise PolicyParseError("Policy metadata chunks must be a non-empty list")
    for item in chunks:
        if not isinstance(item, dict) or set(item) != _CHUNK_FIELDS:
            raise PolicyParseError(
                "Each metadata chunk requires policy_id, section_id, search_terms, "
                "and eligibility"
            )
    return chunks


def _parse_eligibility(value: Any, policy_id: str) -> PolicyEligibility:
    if not isinstance(value, dict) or set(value) != _ELIGIBILITY_FIELDS:
        raise PolicyParseError(
            f"Policy '{policy_id}' has invalid eligibility fields"
        )

    min_level = _required_positive_integer(value, "min_job_level", policy_id)
    max_level = _required_positive_integer(value, "max_job_level", policy_id)
    if min_level > max_level:
        raise PolicyParseError(
            f"Policy '{policy_id}' min_job_level must not exceed max_job_level"
        )

    return PolicyEligibility(
        countries=_required_string_set(value, "countries", policy_id),
        companies=_required_string_set(value, "companies", policy_id),
        employee_types=_required_string_set(value, "employee_types", policy_id),
        min_job_level=min_level,
        max_job_level=max_level,
    )


def _required_string(value: dict[str, Any], field_name: str) -> str:
    field_value = value.get(field_name)
    if not isinstance(field_value, str) or not field_value.strip():
        raise PolicyParseError(f"{field_name} must be a non-empty string")
    return field_value.strip()


def _required_string_set(
    value: dict[str, Any],
    field_name: str,
    policy_id: str,
) -> frozenset[str]:
    field_value = value.get(field_name)
    if (
        not isinstance(field_value, list)
        or not field_value
        or any(not isinstance(item, str) or not item.strip() for item in field_value)
    ):
        raise PolicyParseError(
            f"Policy '{policy_id}' {field_name} must be a non-empty string list"
        )
    return frozenset(item.strip().upper() for item in field_value)


def _required_string_tuple(
    value: dict[str, Any],
    field_name: str,
    policy_id: str,
) -> tuple[str, ...]:
    field_value = value.get(field_name)
    if (
        not isinstance(field_value, list)
        or not field_value
        or any(not isinstance(item, str) or not item.strip() for item in field_value)
    ):
        raise PolicyParseError(
            f"Policy '{policy_id}' {field_name} must be a non-empty string list"
        )
    return tuple(item.strip() for item in field_value)


def _required_positive_integer(
    value: dict[str, Any],
    field_name: str,
    policy_id: str,
) -> int:
    field_value = value.get(field_name)
    if (
        not isinstance(field_value, int)
        or isinstance(field_value, bool)
        or field_value < 1
    ):
        raise PolicyParseError(
            f"Policy '{policy_id}' {field_name} must be a positive integer"
        )
    return field_value
