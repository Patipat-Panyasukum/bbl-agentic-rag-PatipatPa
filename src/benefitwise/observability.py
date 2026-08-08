"""Trace configuration and graph-diagram helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig

WORKFLOW_NAME = "benefitwise_two_agent_workflow"


@dataclass(frozen=True, slots=True)
class DiagramExport:
    mermaid_path: Path
    png_path: Path
    png_bytes: int


def build_run_config(
    *,
    source: str,
    employee_id: str,
    case_id: str | None = None,
) -> RunnableConfig:
    """Build inherited LangSmith labels without copying query or evidence text."""

    normalized_source = _required_label(source, "source").lower()
    normalized_employee_id = _required_label(employee_id, "employee_id").upper()
    normalized_case_id = (
        _required_label(case_id, "case_id") if case_id is not None else None
    )

    tags = ["benefitwise", "two-agent-rag", f"source:{normalized_source}"]
    metadata: dict[str, str] = {
        "workflow": WORKFLOW_NAME,
        "source": normalized_source,
        "employee_id": normalized_employee_id,
    }
    if normalized_case_id:
        tags.append(f"case:{normalized_case_id}")
        metadata["case_id"] = normalized_case_id

    # RunnableConfig metadata and tags are inherited by graph child runs.
    return {
        "run_name": f"benefitwise.{normalized_source}",
        "tags": tags,
        "metadata": metadata,
    }


def export_graph_diagram(
    graph: Any,
    mermaid_path: str | Path,
    png_path: str | Path,
) -> DiagramExport:
    """Export Mermaid source and a PNG from the same compiled LangGraph."""

    drawable = graph.get_graph()
    mermaid = drawable.draw_mermaid()
    png = drawable.draw_mermaid_png()
    if not mermaid.strip():
        raise ValueError("compiled graph returned empty Mermaid source")
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("compiled graph did not return a valid PNG")

    resolved_mermaid_path = Path(mermaid_path)
    resolved_png_path = Path(png_path)
    resolved_mermaid_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_png_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_mermaid_path.write_text(mermaid, encoding="utf-8")
    resolved_png_path.write_bytes(png)
    return DiagramExport(
        mermaid_path=resolved_mermaid_path,
        png_path=resolved_png_path,
        png_bytes=len(png),
    )


def _required_label(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()
