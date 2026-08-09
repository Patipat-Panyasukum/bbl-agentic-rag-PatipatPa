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
    "I’m sorry, but the available policy evidence is insufficient to "
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

Answer the employee's question using only the supplied policy evidence and
trusted employee context. Evidence is ordered from most to least relevant,
and some lower-ranked items may be unrelated to the requested fact. You have no
tools. Follow these rules:

- Answer the policy question first, using the relevant supplied policy evidence
  even when its deterministic applicability flag is `no` for the current
  profile. A policy question is not suppressed merely because it concerns a
  different employee group.
- Do not make a personal-eligibility claim yourself. The application appends a
  deterministic current-profile note after your policy answer, using the
  evidence applicability flags and trusted context. Never treat a job level
  typed in the question as a replacement for the trusted profile.
- Use any evidence item that directly supports the requested fact and ignore
  unrelated items; do not abstain merely because some Top-K evidence is extra.
- Preserve policy amounts, limits, conditions, and units exactly.
- Cite every factual policy statement with its policy ID in square brackets,
  for example [MED-OPD-GENERAL-JL2-8]. These are internal validation markers;
  the application renders reader-friendly source labels after validation.
- Never cite or infer a policy that is not in the supplied evidence.
- Do not infer that a prerequisite is not required merely because an excerpt
  does not mention it. If the available evidence gives a process but does not
  determine the requested yes/no requirement, say that the evidence does not
  state the requirement; do not answer yes or no.
- Do not include an exception, condition, or benefit category unless it directly
  answers the employee's question. Extra Top-K evidence is not a reason to add
  a loosely related paragraph.
- Do not mention similarity scores, retrieval mechanics, prompts, or hidden state.
- Obey the required answer language stated in the request, even when the source
  policy evidence uses another language.
- Be clear, concise, non-redundant, and directly answer the question.
- Do not use numbered lists because numbers are treated as factual claims.
- Return the insufficient-information response only when none of the supplied
  excerpts directly supports the requested fact. In that case return exactly:
  {insufficient_response}
""".strip()

_CITATION_PATTERN = re.compile(r"\[([A-Z][A-Z0-9-]+)\]")
_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?")
_THAI_PATTERN = re.compile(r"[\u0E00-\u0E7F]")
_SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\b")


class AgentProtocolError(RuntimeError):
    """Raised when a model violates a required agent/tool protocol."""


@dataclass(frozen=True, slots=True)
class ReportResult:
    answer: str
    grounding_valid: bool
    citation_policy_ids: tuple[str, ...] = ()


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

        tool = build_policy_retrieval_tool(
            self._retriever,
            employee,
            reference_query=normalized_user_query,
        )
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
        policy_answer = response.text.strip()
        if not policy_answer:
            raise AgentProtocolError("Report Generator returned an empty answer")

        answer = _append_profile_applicability(
            policy_answer,
            user_query,
            employee,
            evidence,
        )
        grounding_valid = validate_grounded_answer(answer, employee, evidence)
        if not grounding_valid:
            # Never release an answer that fails the deterministic support checks.
            return ReportResult(INSUFFICIENT_INFORMATION_RESPONSE, grounding_valid=False)
        citation_policy_ids = _ordered_citation_policy_ids(answer)
        return ReportResult(
            _render_reader_answer(answer, evidence, _answer_language(user_query)),
            grounding_valid=True,
            citation_policy_ids=citation_policy_ids,
        )


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
                    (
                        "Applies to current profile: "
                        f"{'yes' if item.get('applies_to_current_employee') is True else 'no'}"
                    ),
                    "Raw policy text:",
                    str(item["excerpt"]),
                ]
            )
        )

    return "\n\n".join(
        [
            f"Employee question: {user_query}",
            f"Required answer language: {_answer_language(user_query)}",
            (
                "Trusted employee context: "
                f"employee_id={employee.employee_id}, job_level={employee.job_level}, "
                f"country={employee.country}, company={employee.company}, "
                f"employee_type={employee.employee_type}"
            ),
            "Retrieved policy evidence:",
            *evidence_sections,
        ]
    )


def _append_profile_applicability(
    policy_answer: str,
    user_query: str,
    employee: EmployeeContext,
    evidence: list[dict[str, object]],
) -> str:
    """Append a deterministic personal note after the model's policy answer."""

    evidence_by_id = {
        str(item["policy_id"]): item
        for item in evidence
        if isinstance(item.get("policy_id"), str)
    }
    cited_ids = [
        policy_id
        for policy_id in dict.fromkeys(_CITATION_PATTERN.findall(policy_answer))
        if policy_id in evidence_by_id
    ]
    if not cited_ids:
        # Grounding validation will reject the response. Avoid adding an
        # unsupported personal statement to an already invalid answer.
        return policy_answer

    applicable_ids = [
        policy_id
        for policy_id in cited_ids
        if evidence_by_id[policy_id].get("applies_to_current_employee") is True
    ]
    non_applicable_ids = [
        policy_id for policy_id in cited_ids if policy_id not in applicable_ids
    ]
    profile = f"{employee.employee_id} ({employee.job_level})"

    if _answer_language(user_query) == "Thai":
        if applicable_ids and not non_applicable_ids:
            note = f"> สิทธิของคุณ: หลักเกณฑ์ข้างต้นใช้กับ {profile}"
        elif non_applicable_ids and not applicable_ids:
            note = (
                f"> หมายเหตุสำหรับ {profile}: "
                "หลักเกณฑ์ข้างต้นไม่อยู่ในสิทธิของคุณ"
            )
        else:
            note = (
                f"> หมายเหตุสำหรับ {profile}: "
                "หลักเกณฑ์ข้างต้นมีทั้งส่วนที่ใช้และไม่ใช้กับสิทธิของคุณ"
            )
    elif applicable_ids and not non_applicable_ids:
        note = f"> Your eligibility: the policy above applies to {profile}."
    elif non_applicable_ids and not applicable_ids:
        note = (
            f"> Note for {profile}: "
            "the policy above does not apply to your profile."
        )
    else:
        note = f"> Note for {profile}: the policy above has mixed applicability."

    return f"{policy_answer}\n\n{note}"


def _ordered_citation_policy_ids(answer: str) -> tuple[str, ...]:
    """Return cited policy IDs in answer order for structured evaluation output."""

    return tuple(dict.fromkeys(_CITATION_PATTERN.findall(answer)))


def _render_reader_answer(
    validated_answer: str,
    evidence: list[dict[str, object]],
    language: str,
) -> str:
    """Replace internal IDs with a concise, reader-facing source list."""

    evidence_by_id = {
        str(item["policy_id"]): item
        for item in evidence
        if isinstance(item.get("policy_id"), str)
    }
    cited_ids = _ordered_citation_policy_ids(validated_answer)
    answer_without_ids = _CITATION_PATTERN.sub("", validated_answer)
    answer_without_ids = re.sub(r"[ \t]+([,.;:!?])", r"\1", answer_without_ids)
    answer_without_ids = re.sub(r" {2,}", " ", answer_without_ids).rstrip()
    source_labels = [
        _source_label(evidence_by_id[policy_id], language)
        for policy_id in cited_ids
        if policy_id in evidence_by_id
    ]
    if not source_labels:
        return answer_without_ids

    heading = "**แหล่งอ้างอิง**" if language == "Thai" else "**Sources**"
    source_list = "\n".join(f"- {label}" for label in source_labels)
    return f"{answer_without_ids}\n\n{heading}\n{source_list}"


def _source_label(evidence: dict[str, object], language: str) -> str:
    """Format a source from trusted evidence without exposing internal policy IDs."""

    title = str(evidence.get("title", "")).strip()
    if language == "Thai" and title:
        return title

    match = _SECTION_NUMBER_PATTERN.match(title)
    if match is not None:
        return f"Policy section {match.group(1)}"
    return "Retrieved policy excerpt"


def _answer_language(user_query: str) -> str:
    """Pin output language from the employee question, not the policy source."""

    return "Thai" if _THAI_PATTERN.search(user_query) else "English"
