"""LangChain tool adapter for employee-bound policy retrieval."""

from __future__ import annotations

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from benefitwise.employee import EmployeeContext
from benefitwise.retrieval import PolicyEvidence, PolicyRetriever


class PolicyRetrievalInput(BaseModel):
    """Arguments the Data Retriever Agent is allowed to choose."""

    query: str = Field(description="Focused benefit-policy search query")
    top_k: int = Field(default=3, ge=1, le=10, description="Maximum evidence items")


def build_policy_retrieval_tool(
    retriever: PolicyRetriever,
    employee: EmployeeContext,
) -> BaseTool:
    """Bind trusted employee context and expose only search intent to the LLM."""

    def retrieve_benefit_policies(
        query: str,
        top_k: int = 3,
    ) -> tuple[str, list[dict[str, object]]]:
        """Retrieve raw benefit-policy evidence eligible for this employee."""

        # Employee context comes from the authenticated/demo session closure.
        # It is deliberately absent from the model-visible argument schema.
        evidence = retriever.retrieve(query, employee, top_k=top_k)
        content = format_policy_evidence(evidence)
        artifact = [item.as_dict() for item in evidence]
        return content, artifact

    return StructuredTool.from_function(
        func=retrieve_benefit_policies,
        name="retrieve_benefit_policies",
        description=(
            "Search the local employee-benefit knowledge base and return only "
            "policy evidence eligible for the current employee."
        ),
        args_schema=PolicyRetrievalInput,
        response_format="content_and_artifact",
    )


def format_policy_evidence(evidence: tuple[PolicyEvidence, ...]) -> str:
    """Format evidence for an agent while retaining policy IDs and raw text."""

    if not evidence:
        return "No eligible relevant policy evidence was found in the knowledge base."

    sections = []
    for rank, item in enumerate(evidence, start=1):
        sections.append(
            "\n".join(
                [
                    f"[Evidence {rank}]",
                    f"Policy ID: {item.policy_id}",
                    f"Title: {item.title}",
                    f"Similarity: {item.similarity_score:.4f}",
                    "Raw policy text:",
                    item.excerpt,
                ]
            )
        )
    return "\n\n".join(sections)
