"use client";

import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";
import { v4 as uuidv4 } from "uuid";
import type {
  AIMessage,
  Checkpoint,
  Message,
  ToolMessage,
} from "@langchain/langgraph-sdk";
import { parseAsBoolean, useQueryState } from "nuqs";
import { ArrowDown, LoaderCircle, SendHorizontal } from "lucide-react";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import { toast } from "sonner";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import { useStreamContext } from "@/providers/Stream";
import {
  DO_NOT_RENDER_ID_PREFIX,
  ensureToolCallsHaveResponses,
} from "@/lib/ensure-tool-responses";
import { Button } from "@/components/ui/button";
import { BenefitWiseLogo } from "@/components/brand/benefitwise-logo";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { AssistantMessage, AssistantMessageLoading } from "./messages/ai";
import { HumanMessage } from "./messages/human";
import { AgentActivityLog } from "./activity-log";
import { getContentString } from "./utils";

const SUGGESTED_QUESTIONS = [
  "ค่ารักษาพยาบาลผู้ป่วยนอกเบิกได้เท่าไร",
  "What is the inpatient room and food limit?",
  "ต้องใช้สิทธิประกันสังคมก่อนหรือไม่",
];

function StickyContent({
  content,
  footer,
}: {
  content: ReactNode;
  footer: ReactNode;
}) {
  const context = useStickToBottomContext();
  return (
    <>
      <div ref={context.scrollRef} className="chat-scroll">
        <div ref={context.contentRef} className="chat-messages">
          {content}
        </div>
      </div>
      {footer}
    </>
  );
}

function ScrollToBottom() {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();
  if (isAtBottom) return null;

  return (
    <Button
      variant="outline"
      className="absolute bottom-full left-1/2 mb-4 -translate-x-1/2 rounded-full bg-white shadow-sm"
      onClick={() => scrollToBottom()}
    >
      <ArrowDown aria-hidden="true" className="size-4" />
      Scroll to bottom
    </Button>
  );
}

function hasCompletedReport(messages: Message[], toolCallIndex: number) {
  for (const message of messages.slice(toolCallIndex + 1)) {
    if (message.type === "human") return false;
    if (
      message.type === "ai" &&
      getContentString(message.content).trim().length > 0 &&
      (!Array.isArray(message.tool_calls) || message.tool_calls.length === 0)
    ) {
      return true;
    }
  }
  return false;
}

function findToolResult(
  messages: Message[],
  toolCallMessage: AIMessage,
): ToolMessage | undefined {
  const callIds = new Set(
    (toolCallMessage.tool_calls ?? [])
      .map((toolCall) => toolCall.id)
      .filter((id): id is string => typeof id === "string"),
  );
  return messages.find(
    (message): message is ToolMessage =>
      message.type === "tool" && callIds.has(message.tool_call_id),
  );
}

export function Thread() {
  const { profile } = useEmployeeSession();
  const stream = useStreamContext();
  const messages = stream.messages;
  const isLoading = stream.isLoading;
  const [input, setInput] = useState("");
  const [firstTokenReceived, setFirstTokenReceived] = useState(false);
  const [hideToolCalls, setHideToolCalls] = useQueryState(
    "hideToolCalls",
    parseAsBoolean.withDefault(false),
  );
  const previousMessageLength = useRef(0);
  const lastError = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!stream.error) {
      lastError.current = undefined;
      return;
    }
    const message =
      (stream.error as { message?: string }).message || "Unknown graph error";
    if (lastError.current === message) return;
    lastError.current = message;
    toast.error("BenefitWise could not complete this request", {
      description: message,
      closeButton: true,
    });
  }, [stream.error]);

  useEffect(() => {
    if (
      messages.length !== previousMessageLength.current &&
      messages.at(-1)?.type === "ai"
    ) {
      setFirstTokenReceived(true);
    }
    previousMessageLength.current = messages.length;
  }, [messages]);

  if (!profile) return null;

  const submitQuestion = (question: string) => {
    const normalized = question.trim();
    if (!normalized || isLoading || stream.serverStatus !== "online") return;
    setFirstTokenReceived(false);

    const newHumanMessage: Message = {
      id: uuidv4(),
      type: "human",
      content: normalized,
    };
    const toolMessages = ensureToolCallsHaveResponses(messages);

    stream.submit(
      {
        employee_id: profile.employeeId,
        messages: [...toolMessages, newHumanMessage],
      },
      {
        streamMode: ["values"],
        optimisticValues: (previous) => ({
          ...previous,
          employee_id: profile.employeeId,
          messages: [
            ...(previous.messages ?? []),
            ...toolMessages,
            newHumanMessage,
          ],
        }),
      },
    );
    setInput("");
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submitQuestion(input);
  };

  const handleRegenerate = (
    parentCheckpoint: Checkpoint | null | undefined,
  ) => {
    previousMessageLength.current -= 1;
    setFirstTokenReceived(false);
    stream.submit(
      { employee_id: profile.employeeId },
      { checkpoint: parentCheckpoint, streamMode: ["values"] },
    );
  };

  const visibleMessages = messages.filter(
    (message) => !message.id?.startsWith(DO_NOT_RENDER_ID_PREFIX),
  );
  const chatStarted = visibleMessages.length > 0;
  const hasNoAIOrToolMessages = !messages.some(
    (message) => message.type === "ai" || message.type === "tool",
  );
  const groupedToolCallIds = new Set(
    visibleMessages.flatMap((message) =>
      message.type === "ai" && Array.isArray(message.tool_calls)
        ? message.tool_calls
            .map((toolCall) => toolCall.id)
            .filter((id): id is string => typeof id === "string")
        : [],
    ),
  );

  return (
    <section className="relative flex min-h-0 flex-1" aria-label="Chat">
      <StickToBottom className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        <StickyContent
          content={
            <>
              {!chatStarted && (
                <div className="empty-chat">
                  <BenefitWiseLogo className="empty-chat-mark" priority />
                  <h1>How can I help with your benefits?</h1>
                  <p>
                    Ask a policy question for {profile.employeeId}. The policy
                    answer comes first; current-profile applicability follows.
                  </p>
                  <div className="suggested-questions">
                    {SUGGESTED_QUESTIONS.map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => submitQuestion(question)}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {visibleMessages.map((message, index) => {
                const key = message.id || `${message.type}-${index}`;
                if (message.type === "human") {
                  return (
                    <HumanMessage
                      key={key}
                      message={message}
                      isLoading={isLoading}
                    />
                  );
                }

                if (
                  message.type === "ai" &&
                  Array.isArray(message.tool_calls) &&
                  message.tool_calls.length > 0
                ) {
                  if (hideToolCalls) return null;
                  return (
                    <AgentActivityLog
                      key={key}
                      message={message}
                      toolResult={findToolResult(visibleMessages, message)}
                      isLoading={isLoading}
                      reportComplete={hasCompletedReport(
                        visibleMessages,
                        index,
                      )}
                    />
                  );
                }

                // Paired tool results are rendered inside the activity log.
                if (
                  message.type === "tool" &&
                  groupedToolCallIds.has(message.tool_call_id)
                ) {
                  return null;
                }

                return (
                  <AssistantMessage
                    key={key}
                    message={message}
                    isLoading={isLoading}
                    handleRegenerate={handleRegenerate}
                  />
                );
              })}

              {hasNoAIOrToolMessages && !!stream.interrupt && (
                <AssistantMessage
                  message={undefined}
                  isLoading={isLoading}
                  handleRegenerate={handleRegenerate}
                />
              )}
              {isLoading && !firstTokenReceived && <AssistantMessageLoading />}
            </>
          }
          footer={
            <div className="chat-composer-zone">
              <ScrollToBottom />
              <form onSubmit={handleSubmit} className="chat-composer">
                <label className="sr-only" htmlFor="benefit-question">
                  Ask a benefits question
                </label>
                <textarea
                  id="benefit-question"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                  placeholder="Ask a benefits question..."
                  rows={2}
                />
                <div className="chat-composer-actions">
                  <div className="flex items-center gap-2">
                    <Switch
                      id="hide-tool-calls"
                      checked={hideToolCalls}
                      onCheckedChange={setHideToolCalls}
                    />
                    <Label
                      htmlFor="hide-tool-calls"
                      className="text-sm text-muted-foreground"
                    >
                      Hide tool calls
                    </Label>
                  </div>
                  {isLoading ? (
                    <Button type="button" onClick={() => stream.stop()}>
                      <LoaderCircle
                        aria-hidden="true"
                        className="size-4 animate-spin"
                      />
                      Stop
                    </Button>
                  ) : (
                    <Button
                      type="submit"
                      disabled={
                        !input.trim() || stream.serverStatus !== "online"
                      }
                    >
                      Send
                      <SendHorizontal aria-hidden="true" className="size-4" />
                    </Button>
                  )}
                </div>
              </form>
              <p>
                Answers use retrieved demo policy evidence. Verify official
                terms before making a claim.
              </p>
            </div>
          }
        />
      </StickToBottom>
    </section>
  );
}
