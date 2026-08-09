"""Sequential LangGraph orchestration for the two-agent BenefitWise workflow."""

from __future__ import annotations

from typing import Annotated, Any, Required, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from benefitwise.agents import AgentProtocolError, DataRetrieverAgent, ReportGeneratorAgent
from benefitwise.employee import EmployeeContext
from benefitwise.employee_repository import SQLiteEmployeeRepository
from benefitwise.retrieval import PolicyRetriever
from benefitwise.retrieval_tool import build_policy_retrieval_tool


class BenefitWiseInput(TypedDict, total=False):
    employee_id: Required[str]
    user_query: str
    messages: list[BaseMessage]


class BenefitWiseOutput(TypedDict, total=False):
    employee_context: EmployeeContext
    retrieval_query: str
    evidence: list[dict[str, object]]
    final_answer: str
    grounding_valid: bool
    messages: list[BaseMessage]


class BenefitWiseState(TypedDict, total=False):
    employee_id: Required[str]
    user_query: str
    messages: Annotated[list[BaseMessage], add_messages]
    employee_context: EmployeeContext
    retrieval_tool_call: dict[str, Any]
    retrieval_query: str
    retrieval_tool_content: str
    evidence: list[dict[str, object]]
    final_answer: str
    grounding_valid: bool


def _current_user_query(state: BenefitWiseState) -> str:
    """Resolve the latest chat question while preserving the CLI contract."""

    for message in reversed(state.get("messages", [])):
        if not isinstance(message, HumanMessage):
            continue
        if not isinstance(message.content, str):
            raise ValueError("The latest human message must contain plain text")
        question = message.content.strip()
        if not question:
            raise ValueError("The latest human message must not be blank")
        return question

    user_query = state.get("user_query")
    if not isinstance(user_query, str):
        raise ValueError("Provide user_query or a human message")
    question = user_query.strip()
    if not question:
        raise ValueError("user_query must not be blank")
    return question


def build_benefit_graph(
    employee_repository: SQLiteEmployeeRepository,
    retriever: PolicyRetriever,
    retriever_model: Any,
    report_model: Any,
    *,
    top_k: int = 3,
):
    """Compile the deterministic-to-agent-to-tool-to-agent workflow."""

    retriever_agent = DataRetrieverAgent(retriever_model, retriever, top_k=top_k)
    report_agent = ReportGeneratorAgent(report_model)

    def resolve_employee(state: BenefitWiseState) -> dict[str, object]:
        # Identity resolution occurs before either LLM sees the request.
        return {
            "employee_context": employee_repository.get_by_id(state["employee_id"]),
            "user_query": _current_user_query(state),
        }

    def data_retriever_agent(state: BenefitWiseState) -> dict[str, object]:
        tool_call = retriever_agent.create_tool_call(
            state["user_query"], state["employee_context"]
        )
        update: dict[str, object] = {
            "retrieval_tool_call": tool_call,
            "retrieval_query": str(tool_call["args"]["query"]),
        }
        if state.get("messages"):
            # Agent Chat UI renders this genuine model-selected tool call.
            update["messages"] = [AIMessage(content="", tool_calls=[tool_call])]
        return update

    def retrieval_tool(state: BenefitWiseState) -> dict[str, object]:
        # Rebuild the employee-bound tool from trusted state instead of storing
        # a non-serializable tool object inside LangGraph state.
        tool = build_policy_retrieval_tool(
            retriever,
            state["employee_context"],
            reference_query=state["user_query"],
        )
        result = tool.invoke(state["retrieval_tool_call"])
        if not isinstance(result, ToolMessage):
            raise AgentProtocolError("Retrieval tool did not return a ToolMessage")
        artifact = result.artifact
        if not isinstance(artifact, list):
            raise AgentProtocolError("Retrieval tool returned an invalid evidence artifact")
        update: dict[str, object] = {
            "retrieval_tool_content": str(result.content),
            "evidence": artifact,
        }
        if state.get("messages"):
            update["messages"] = [result]
        return update

    def report_generator_agent(state: BenefitWiseState) -> dict[str, object]:
        report = report_agent.generate(
            state["user_query"],
            state["employee_context"],
            state["evidence"],
        )
        update: dict[str, object] = {
            "final_answer": report.answer,
            "grounding_valid": report.grounding_valid,
        }
        if state.get("messages"):
            update["messages"] = [AIMessage(content=report.answer)]
        return update

    workflow = StateGraph(
        BenefitWiseState,
        input_schema=BenefitWiseInput,
        output_schema=BenefitWiseOutput,
    )
    workflow.add_node("resolve_employee", resolve_employee)
    workflow.add_node("data_retriever_agent", data_retriever_agent)
    workflow.add_node("retrieval_tool", retrieval_tool)
    workflow.add_node("report_generator_agent", report_generator_agent)
    workflow.add_edge(START, "resolve_employee")
    workflow.add_edge("resolve_employee", "data_retriever_agent")
    workflow.add_edge("data_retriever_agent", "retrieval_tool")
    workflow.add_edge("retrieval_tool", "report_generator_agent")
    workflow.add_edge("report_generator_agent", END)
    return workflow.compile(name="benefitwise_two_agent_workflow")
