"""LangGraph CLI/Studio entry point."""

from benefitwise.application import create_default_graph

# LangGraph CLI discovers this compiled graph through langgraph.json.
graph = create_default_graph()
