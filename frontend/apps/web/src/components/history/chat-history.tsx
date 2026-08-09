"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { Message, Thread as GraphThread } from "@langchain/langgraph-sdk";
import {
  ArrowUpRight,
  Clock3,
  FileSearch2,
  History,
  LoaderCircle,
  MessageCircle,
  RefreshCw,
} from "lucide-react";
import { BenefitWiseLogo } from "@/components/brand/benefitwise-logo";
import { EmployeeProfileMenu } from "@/components/employee/employee-profile-menu";
import { ProfileAvatar } from "@/components/employee/profile-avatar";
import { Button } from "@/components/ui/button";
import { getContentString } from "@/components/thread/utils";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import { useThreads } from "@/providers/Thread";

type HistorySummary = {
  answer: string;
  employeeId: string | null;
  question: string;
  status: GraphThread["status"];
  threadId: string;
  updatedAt: string;
};

function getMessages(values: unknown): Message[] {
  if (!values || typeof values !== "object") return [];
  const candidate = (values as { messages?: unknown }).messages;
  if (!Array.isArray(candidate)) return [];

  return candidate.filter(
    (message): message is Message =>
      Boolean(message) &&
      typeof message === "object" &&
      "type" in message &&
      "content" in message,
  );
}

function getThreadEmployeeId(values: unknown): string | null {
  if (!values || typeof values !== "object") return null;
  const employeeId = (values as { employee_id?: unknown }).employee_id;
  return typeof employeeId === "string" ? employeeId : null;
}

function findLatestContent(messages: Message[], type: "human" | "ai") {
  for (const message of messages.toReversed()) {
    if (message.type !== type) continue;
    if (
      type === "ai" &&
      Array.isArray((message as { tool_calls?: unknown }).tool_calls) &&
      (message as { tool_calls: unknown[] }).tool_calls.length > 0
    ) {
      continue;
    }
    const content = getContentString(message.content).trim();
    if (content) return content;
  }
  return "";
}

function summarizeThread(thread: GraphThread): HistorySummary {
  const messages = getMessages(thread.values);
  return {
    answer: findLatestContent(messages, "ai"),
    employeeId: getThreadEmployeeId(thread.values),
    question: findLatestContent(messages, "human"),
    status: thread.status,
    threadId: thread.thread_id,
    updatedAt: thread.updated_at,
  };
}

function formatUpdatedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "Updated recently";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function preview(value: string, fallback: string) {
  if (!value) return fallback;
  return value.length > 180 ? `${value.slice(0, 177).trimEnd()}…` : value;
}

export function ChatHistory() {
  const { profile } = useEmployeeSession();
  const { getThreads, setThreads, setThreadsLoading, threads, threadsLoading } =
    useThreads();
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setThreadsLoading(true);
    setError(null);
    try {
      setThreads(await getThreads());
    } catch {
      setError(
        "Could not load the saved local conversations. Check the graph server and retry.",
      );
    } finally {
      setThreadsLoading(false);
    }
  }, [getThreads, setThreads, setThreadsLoading]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const sessions = useMemo(
    () =>
      threads
        .map(summarizeThread)
        .filter((thread) => thread.employeeId === profile?.employeeId)
        .sort(
          (left, right) =>
            new Date(right.updatedAt).valueOf() -
            new Date(left.updatedAt).valueOf(),
        ),
    [profile?.employeeId, threads],
  );

  if (!profile) return null;

  return (
    <main className="history-shell">
      <header className="chat-header">
        <Link className="chat-brand" href="/chat" aria-label="Return to chat">
          <BenefitWiseLogo className="chat-brand-mark" priority />
          <span>BenefitWise</span>
        </Link>

        <div className="chat-header-actions">
          <Link
            className="icon-button"
            href="/chat"
            aria-label="Return to chat"
            title="Return to chat"
          >
            <MessageCircle aria-hidden="true" className="size-5" />
          </Link>
          <EmployeeProfileMenu />
        </div>
      </header>

      <section className="history-content" aria-labelledby="history-heading">
        <div className="history-heading">
          <div className="history-heading-icon" aria-hidden="true">
            <History className="size-5" />
          </div>
          <div>
            <p className="history-eyebrow">Saved LangGraph threads</p>
            <h1 id="history-heading">Chat history</h1>
            <p>
              A private local log for {profile.employeeId}. Each item opens the
              original conversation and its retrieved evidence.
            </p>
          </div>
          <div className="history-heading-actions">
            <Button
              variant="outline"
              size="sm"
              type="button"
              onClick={() => void refresh()}
              disabled={threadsLoading}
            >
              <RefreshCw
                aria-hidden="true"
                className={threadsLoading ? "size-4 animate-spin" : "size-4"}
              />
              Refresh
            </Button>
            <Button asChild size="sm">
              <Link href="/chat">
                New chat
                <ArrowUpRight aria-hidden="true" className="size-4" />
              </Link>
            </Button>
          </div>
        </div>

        <div className="history-profile-strip">
          <ProfileAvatar profile={profile} size="history" />
          <span>
            <strong>{profile.employeeId}</strong>
            <small>
              {profile.jobLevel} · {profile.employeeType} · {profile.country}
            </small>
          </span>
          <span className="history-count">
            {sessions.length} saved conversation
            {sessions.length === 1 ? "" : "s"}
          </span>
        </div>

        {error && (
          <div className="history-message history-message-error" role="alert">
            {error}
          </div>
        )}

        {threadsLoading && sessions.length === 0 ? (
          <div className="history-message" role="status">
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            Loading saved conversations...
          </div>
        ) : sessions.length === 0 ? (
          <div className="history-empty">
            <FileSearch2 aria-hidden="true" className="size-6" />
            <h2>No saved conversations yet</h2>
            <p>
              Ask a benefits question to create a LangGraph conversation log for
              this fictional profile.
            </p>
            <Button asChild>
              <Link href="/chat">Start a benefits chat</Link>
            </Button>
          </div>
        ) : (
          <ol className="history-list">
            {sessions.map((session) => (
              <li key={session.threadId} className="history-item">
                <div className="history-item-marker" aria-hidden="true">
                  <Clock3 className="size-4" />
                </div>
                <article>
                  <div className="history-item-meta">
                    <time dateTime={session.updatedAt}>
                      {formatUpdatedAt(session.updatedAt)}
                    </time>
                    <span data-status={session.status}>{session.status}</span>
                  </div>
                  <h2>{preview(session.question, "Conversation started")}</h2>
                  <p>
                    {preview(session.answer, "Awaiting a grounded response.")}
                  </p>
                  <Link
                    className="history-open-link"
                    href={`/chat?threadId=${encodeURIComponent(session.threadId)}`}
                  >
                    Open conversation
                    <ArrowUpRight aria-hidden="true" className="size-4" />
                  </Link>
                </article>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
