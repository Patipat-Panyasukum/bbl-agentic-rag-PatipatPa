"use client";

import { useEffect, useState } from "react";
import type { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import {
  Check,
  ChevronDown,
  Circle,
  Database,
  FileCheck2,
  LoaderCircle,
  Search,
  UserRoundCheck,
} from "lucide-react";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import {
  type EmployeeContextState,
  type StateType,
  useStreamContext,
} from "@/providers/Stream";
import { getContentString } from "./utils";

type ToolCallShape = {
  name?: string;
  args?: Record<string, unknown>;
};

function StepStatus({
  complete,
  active,
}: {
  complete: boolean;
  active: boolean;
}) {
  if (complete) {
    return <Check aria-hidden="true" className="size-3.5" strokeWidth={2.5} />;
  }
  if (active) {
    return (
      <LoaderCircle aria-hidden="true" className="size-3.5 animate-spin" />
    );
  }
  return <Circle aria-hidden="true" className="size-3.5" />;
}

function employeeLabel(
  context: EmployeeContextState | undefined,
  fallbackId: string,
) {
  if (!context) return fallbackId;
  return `${context.employee_id} · ${context.job_level} · ${context.employee_type}`;
}

export function AgentActivityLog({
  message,
  toolResult,
  reportComplete,
  isLoading,
}: {
  message: AIMessage;
  toolResult: ToolMessage | undefined;
  reportComplete: boolean;
  isLoading: boolean;
}) {
  const thread = useStreamContext();
  const { profile } = useEmployeeSession();
  const [expanded, setExpanded] = useState(true);
  const toolCall = message.tool_calls?.[0] as ToolCallShape | undefined;
  const resultText = toolResult ? getContentString(toolResult.content) : "";
  const evidenceCount = (resultText.match(/^\[Evidence \d+\]/gm) ?? []).length;
  const stateAtToolCall = thread.getMessagesMetadata(message)?.firstSeenState
    ?.values as StateType | undefined;
  const employeeContext =
    stateAtToolCall?.employee_context ?? thread.values.employee_context;
  const query =
    typeof toolCall?.args?.query === "string"
      ? toolCall.args.query
      : stateAtToolCall?.retrieval_query;
  const topK = toolCall?.args?.top_k;
  const retrievalComplete = Boolean(toolResult);
  const completedSteps = 2 + Number(retrievalComplete) + Number(reportComplete);
  const toolFailed = toolResult?.status === "error";

  useEffect(() => {
    if (isLoading) setExpanded(true);
  }, [isLoading]);

  return (
    <details
      className="agent-activity"
      open={expanded}
      onToggle={(event) => setExpanded(event.currentTarget.open)}
    >
      <summary>
        <span className="agent-activity-mark" aria-hidden="true">
          <FileCheck2 className="size-4" />
        </span>
        <span className="agent-activity-heading">
          <strong>Agent activity</strong>
          <small>{completedSteps} of 4 observable steps</small>
        </span>
        <span
          className="agent-activity-state"
          data-state={reportComplete ? "complete" : "running"}
        >
          {reportComplete ? "Complete" : "Running"}
        </span>
        <ChevronDown
          aria-hidden="true"
          className="agent-activity-chevron size-4"
        />
      </summary>

      <ol className="agent-activity-steps">
        <li data-state="complete">
          <span className="agent-step-status">
            <StepStatus complete active={false} />
          </span>
          <UserRoundCheck aria-hidden="true" className="agent-step-icon" />
          <div>
            <strong>Employee context resolved</strong>
            <p>
              {employeeLabel(
                employeeContext,
                profile?.employeeId ?? "Employee",
              )}
            </p>
          </div>
        </li>

        <li data-state="complete">
          <span className="agent-step-status">
            <StepStatus complete active={false} />
          </span>
          <Search aria-hidden="true" className="agent-step-icon" />
          <div>
            <strong>Data Retriever Agent</strong>
            <p>
              Planned search{query ? `: ${query}` : ""}
              {typeof topK === "number" ? ` · Top ${topK}` : ""}
            </p>
          </div>
        </li>

        <li
          data-state={
            toolFailed ? "error" : retrievalComplete ? "complete" : "active"
          }
        >
          <span className="agent-step-status">
            <StepStatus
              complete={retrievalComplete && !toolFailed}
              active={!retrievalComplete}
            />
          </span>
          <Database aria-hidden="true" className="agent-step-icon" />
          <div>
            <strong>Retrieval tool</strong>
            <p>
              {toolFailed
                ? "Tool execution failed"
                : retrievalComplete
                  ? evidenceCount > 0
                    ? `Returned ${evidenceCount} policy excerpt${evidenceCount === 1 ? "" : "s"} with profile applicability`
                    : "No policy evidence returned"
                  : "Searching policy evidence…"}
            </p>
            {toolResult && (
              <details className="agent-evidence-details">
                <summary>View retrieved evidence</summary>
                <pre>{resultText}</pre>
              </details>
            )}
          </div>
        </li>

        <li
          data-state={
            reportComplete
              ? "complete"
              : retrievalComplete
                ? "active"
                : "pending"
          }
        >
          <span className="agent-step-status">
            <StepStatus
              complete={reportComplete}
              active={retrievalComplete && !reportComplete}
            />
          </span>
          <FileCheck2 aria-hidden="true" className="agent-step-icon" />
          <div>
            <strong>Report Generator Agent</strong>
            <p>
              {reportComplete
                ? "Final answer added to the conversation"
                : retrievalComplete
                  ? "Generating an answer from retrieved evidence…"
                  : "Waiting for policy evidence"}
            </p>
          </div>
        </li>
      </ol>
    </details>
  );
}
