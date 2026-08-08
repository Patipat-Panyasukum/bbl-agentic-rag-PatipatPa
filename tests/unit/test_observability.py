"""Tests for trace labels and graph artifact export."""

import pytest

from benefitwise.observability import build_run_config, export_graph_diagram


class DrawableGraph:
    def draw_mermaid(self):
        return "graph TD; A --> B;\n"

    def draw_mermaid_png(self):
        return b"\x89PNG\r\n\x1a\nrendered"


class CompiledGraph:
    def get_graph(self):
        return DrawableGraph()


def test_builds_inherited_trace_labels_without_prompt_content() -> None:
    config = build_run_config(
        source="Evaluation",
        employee_id=" e003 ",
        case_id="opd-operations",
    )

    assert config["run_name"] == "benefitwise.evaluation"
    assert config["tags"] == [
        "benefitwise",
        "two-agent-rag",
        "source:evaluation",
        "case:opd-operations",
    ]
    assert config["metadata"] == {
        "workflow": "benefitwise_two_agent_workflow",
        "source": "evaluation",
        "employee_id": "E003",
        "case_id": "opd-operations",
    }
    assert "query" not in config["metadata"]


@pytest.mark.parametrize("field", ["source", "employee_id"])
def test_rejects_blank_trace_labels(field) -> None:
    values = {"source": "cli", "employee_id": "E001"}
    values[field] = "   "

    with pytest.raises(ValueError, match=field):
        build_run_config(**values)


def test_exports_mermaid_and_png_from_same_graph(tmp_path) -> None:
    mermaid_path = tmp_path / "workflow.mmd"
    png_path = tmp_path / "workflow.png"

    result = export_graph_diagram(CompiledGraph(), mermaid_path, png_path)

    assert mermaid_path.read_text(encoding="utf-8") == "graph TD; A --> B;\n"
    assert png_path.read_bytes().startswith(b"\x89PNG")
    assert result.png_bytes == len(png_path.read_bytes())
