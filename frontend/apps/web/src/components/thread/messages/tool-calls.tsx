import { useState } from "react";
import type { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import { ChevronDown, ChevronUp } from "lucide-react";

function readableValue(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function ToolCalls({
  toolCalls,
}: {
  toolCalls: AIMessage["tool_calls"];
}) {
  if (!toolCalls?.length) return null;

  return (
    <div className="grid w-full gap-2">
      {toolCalls.map((toolCall) => (
        <div className="tool-card" key={toolCall.id || toolCall.name}>
          <div className="tool-card-header">
            <span>Tool call</span>
            <code>{toolCall.name}</code>
          </div>
          {Object.keys(toolCall.args ?? {}).length > 0 ? (
            <dl>
              {Object.entries(toolCall.args ?? {}).map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{readableValue(value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <pre>{"{}"}</pre>
          )}
        </div>
      ))}
    </div>
  );
}

export function ToolResult({ message }: { message: ToolMessage }) {
  const [expanded, setExpanded] = useState(false);
  const content = readableValue(message.content);
  const lines = content.split("\n");
  const shouldTruncate = lines.length > 12 || content.length > 900;
  const visibleContent =
    shouldTruncate && !expanded
      ? `${lines.slice(0, 12).join("\n").slice(0, 900).trim()}\n...`
      : content;

  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span>Tool result</span>
        <code>{message.name || "retrieve_benefit_policies"}</code>
      </div>
      <pre>{visibleContent}</pre>
      {shouldTruncate && (
        <button
          className="tool-card-expand"
          type="button"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? (
            <ChevronUp aria-hidden="true" className="size-4" />
          ) : (
            <ChevronDown aria-hidden="true" className="size-4" />
          )}
          {expanded ? "Collapse result" : "Show full result"}
        </button>
      )}
    </div>
  );
}
