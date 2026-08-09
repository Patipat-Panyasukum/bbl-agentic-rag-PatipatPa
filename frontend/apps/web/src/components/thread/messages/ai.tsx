import { useStreamContext } from "@/providers/Stream";
import type { Checkpoint, Message } from "@langchain/langgraph-sdk";
import { parseAsBoolean, useQueryState } from "nuqs";
import { getContentString } from "../utils";
import { BranchSwitcher, CommandBar } from "./shared";
import { MarkdownText } from "../markdown-text";
import { cn } from "@/lib/utils";
import { ToolCalls, ToolResult } from "./tool-calls";

export function AssistantMessage({
  message,
  isLoading,
  handleRegenerate,
}: {
  message: Message | undefined;
  isLoading: boolean;
  handleRegenerate: (parentCheckpoint: Checkpoint | null | undefined) => void;
}) {
  const content = message?.content ?? [];
  const contentString = getContentString(content);
  const [hideToolCalls] = useQueryState(
    "hideToolCalls",
    parseAsBoolean.withDefault(false),
  );
  const thread = useStreamContext();
  const meta = message ? thread.getMessagesMetadata(message) : undefined;
  const parentCheckpoint = meta?.firstSeenState?.parent_checkpoint;
  const isToolResult = message?.type === "tool";
  const toolCalls =
    message?.type === "ai" && Array.isArray(message.tool_calls)
      ? message.tool_calls
      : undefined;

  if (isToolResult && hideToolCalls) return null;

  return (
    <div className="group mr-auto flex w-full items-start gap-2">
      <div className="flex w-full flex-col gap-2">
        {isToolResult ? (
          <ToolResult message={message} />
        ) : (
          <>
            {contentString.length > 0 && (
              <div className="py-1">
                <MarkdownText>{contentString}</MarkdownText>
              </div>
            )}
            {!hideToolCalls && toolCalls && toolCalls.length > 0 && (
              <ToolCalls toolCalls={toolCalls} />
            )}
            <div
              className={cn(
                "mr-auto flex items-center gap-2 transition-opacity",
                "opacity-0 group-focus-within:opacity-100 group-hover:opacity-100",
              )}
            >
              <BranchSwitcher
                branch={meta?.branch}
                branchOptions={meta?.branchOptions}
                onSelect={(branch) => thread.setBranch(branch)}
                isLoading={isLoading}
              />
              <CommandBar
                content={contentString}
                isLoading={isLoading}
                isAiMessage={true}
                handleRegenerate={() => handleRegenerate(parentCheckpoint)}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export function AssistantMessageLoading() {
  return (
    <div className="mr-auto flex items-start gap-2" role="status">
      <span className="sr-only">BenefitWise is working</span>
      <div className="flex h-8 items-center gap-1 rounded-2xl bg-muted px-4 py-2">
        <span className="size-1.5 animate-pulse rounded-full bg-foreground/50" />
        <span className="size-1.5 animate-pulse rounded-full bg-foreground/50 [animation-delay:150ms]" />
        <span className="size-1.5 animate-pulse rounded-full bg-foreground/50 [animation-delay:300ms]" />
      </div>
    </div>
  );
}
