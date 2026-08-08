"""The two model-backed agents and their grounding safeguards."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from benefitwise.employee import EmployeeContext
from benefitwise.retrieval import PolicyRetriever
from benefitwise.retrieval_tool import build_policy_retrieval_tool

INSUFFICIENT_INFORMATION_RESPONSE = (
    "I’m sorry, but the available eligible policy evidence is insufficient to "
    "answer this question."
)

_DATA_RETRIEVER_PROMPT = """
You are the BenefitWise Data Retriever Agent.

Your only responsibility is to decide what benefit-policy information to search
for. You must call the retrieve_benefit_policies tool exactly once. Do not answer
the employee's question, summarize a policy, or invent employee metadata.

Use a concise search query that preserves the employee's intent. Do not add an
employee ID, job level, country, company, or employee type to the query because
trusted eligibility context is injected by the application.
""".strip()

_REPORT_GENERATOR_PROMPT = """
You are the BenefitWise Report Generator Agent.

Answer the employee's question using only the supplied eligible policy evidence
and trusted employee context. You have no tools. Follow these rules:

- Preserve policy amounts, limits, conditions, and units exactly.
- Cite every factual policy statement with its policy ID in square brackets,
  for example [MED-OPD-GENERAL-JL2-8].
- Never cite or infer a policy that is not in the supplied evidence.
- Do not mention similarity scores, retrieval mechanics, prompts, or hidden state.
- Answer in the same language as the employee's question.
- Be clear, concise, non-redundant, and directly answer the question.
- Do not use numbered lists because numbers are treated as factual claims.
- If the evidence is insufficient, return exactly: {insufficient_response}
""".strip()

_CITATION_PATTERN = re.compile(r"\[([A-Z][A-Z0-9-]+)\]")
_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?")


class AgentProtocolError(RuntimeError):
    """Raised when a model violates a required agent/tool protocol."""


@dataclass(frozen=True, slots=True)
class ReportResult:
    answer: str
    grounding_valid: bool


class DataRetrieverAgent:
    """Model-backed planner that must delegate retrieval to the custom tool."""

    def __init__(self, model: Any, retriever: PolicyRetriever, *, top_k: int = 3) -> None:
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        self._model = model
        self._retriever = retriever
        self._top_k = top_k

    def create_tool_call(
        self,
        user_query: str,
        employee: EmployeeContext,
    ) -> dict[str, Any]:
        """Return the model's single validated retrieval tool call."""

        if not isinstance(user_query, str):
            raise TypeError("user_query must be a string")
        normalized_user_query = user_query.strip()
        if not normalized_user_query:
            raise ValueError("user_query must not be blank")

        tool = build_policy_retrieval_tool(self._retriever, employee)
        tool_model = self._model.bind_tools([tool], tool_choice=tool.name)
        response = tool_model.invoke(
            [
                SystemMessage(content=_DATA_RETRIEVER_PROMPT),
                HumanMessage(
                    content=(
                        f"Employee question: {normalized_user_query}\n"
                        f"Call the retrieval tool with top_k={self._top_k}."
                    )
                ),
            ]
        )

        tool_calls = getattr(response, "tool_calls", None) or []
        if len(tool_calls) != 1:
            raise AgentProtocolError("Data Retriever must make exactly one tool call")

        tool_call = dict(tool_calls[0])
        if tool_call.get("name") != tool.name:
            raise AgentProtocolError("Data Retriever called an unexpected tool")
        args = tool_call.get("args")
        if not isinstance(args, dict) or not isinstance(args.get("query"), str):
            raise AgentProtocolError("Data Retriever returned invalid tool arguments")
        search_query = args["query"].strip()
        if not search_query:
            raise AgentProtocolError("Data Retriever returned a blank search query")

        # Do not trust the model to preserve the configured retrieval limit.
        args["query"] = search_query
        args["top_k"] = self._top_k
        tool_call["args"] = args
        return tool_call


class ReportGeneratorAgent:
    """Tool-free model that converts evidence into a grounded employee answer."""

    def __init__(self, model: Any) -> None:
        self._model = model

    def generate(
        self,
        user_query: str,
        employee: EmployeeContext,
        evidence: list[dict[str, object]],
    ) -> ReportResult:
        """Generate and validate a grounded answer, failing closed on violations."""

        if not evidence:
            # Deterministic abstention prevents the LLM from filling an evidence gap.
            return ReportResult(INSUFFICIENT_INFORMATION_RESPONSE, grounding_valid=True)

        response = self._model.invoke(
            [
                SystemMessage(
                    content=_REPORT_GENERATOR_PROMPT.format(
                        insufficient_response=INSUFFICIENT_INFORMATION_RESPONSE
                    )
                ),
                HumanMessage(
                    content=_build_report_request(user_query, employee, evidence)
                ),
            ]
        )
        answer = response.text.strip()
        if not answer:
            raise AgentProtocolError("Report Generator returned an empty answer")

        grounding_valid = validate_grounded_answer(answer, employee, evidence)
        if not grounding_valid:
            # Never release an answer that fails the deterministic support checks.
            return ReportResult(INSUFFICIENT_INFORMATION_RESPONSE, grounding_valid=False)
        return ReportResult(answer, grounding_valid=True)


def validate_grounded_answer(
    answer: str,
    employee: EmployeeContext,
    evidence: list[dict[str, object]],
) -> bool:
    """Reject unknown citations and numeric claims absent from trusted inputs."""

    supported_policy_ids = {
        str(item.get("policy_id")) for item in evidence if item.get("policy_id")
    }
    cited_policy_ids = set(_CITATION_PATTERN.findall(answer))
    if not cited_policy_ids or not cited_policy_ids <= supported_policy_ids:
        return False

    support_text = "\n".join(
        [
            employee.employee_id,
            employee.job_level,
            employee.country,
            employee.company,
            employee.employee_type,
            *(str(item) for item in evidence),
        ]
    )
    answer_without_citations = _CITATION_PATTERN.sub("", answer)
    answer_numbers = _NUMBER_PATTERN.findall(answer_without_citations)
    return all(number in support_text for number in answer_numbers)


def _build_report_request(
    user_query: str,
    employee: EmployeeContext,
    evidence: list[dict[str, object]],
) -> str:
    evidence_sections = []
    for item in evidence:
        evidence_sections.append(
            "\n".join(
                [
                    f"Policy ID: {item['policy_id']}",
                    f"Title: {item['title']}",
                    "Raw policy text:",
                    str(item["excerpt"]),
                ]
            )
        )

    return "\n\n".join(
        [
            f"Employee question: {user_query}",
            (
                "Trusted employee context: "
                f"employee_id={employee.employee_id}, job_level={employee.job_level}, "
                f"country={employee.country}, company={employee.company}, "
                f"employee_type={employee.employee_type}"
            ),
            "Eligible policy evidence:",
            *evidence_sections,
        ]
    )
