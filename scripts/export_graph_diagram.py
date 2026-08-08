"""Export reviewer-facing Mermaid and PNG views of the compiled graph."""

from __future__ import annotations

import argparse
from pathlib import Path

from benefitwise.application import create_default_graph
from benefitwise.observability import export_graph_diagram

DEFAULT_MERMAID_PATH = Path("docs/assets/langgraph-workflow.mmd")
DEFAULT_PNG_PATH = Path("docs/assets/langgraph-workflow.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mermaid-output", type=Path, default=DEFAULT_MERMAID_PATH)
    parser.add_argument("--png-output", type=Path, default=DEFAULT_PNG_PATH)
    args = parser.parse_args()

    exported = export_graph_diagram(
        create_default_graph(),
        args.mermaid_output,
        args.png_output,
    )
    print(f"Mermaid: {exported.mermaid_path}")
    print(f"PNG: {exported.png_path} ({exported.png_bytes} bytes)")


if __name__ == "__main__":
    main()
