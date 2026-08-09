"use client";

import Link from "next/link";
import { useQueryState } from "nuqs";
import { History, SquarePen } from "lucide-react";
import { BenefitWiseLogo } from "@/components/brand/benefitwise-logo";
import { EmployeeProfileMenu } from "@/components/employee/employee-profile-menu";
import { Thread } from "@/components/thread";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import { useStreamContext } from "@/providers/Stream";

function GraphStatus() {
  const { serverStatus } = useStreamContext();
  const label = {
    checking: "Checking graph",
    online: "Graph online",
    offline: "Graph offline",
  }[serverStatus];

  return (
    <span className="graph-status" data-status={serverStatus} title={label}>
      <span aria-hidden="true" />
      <span className="hidden sm:inline">{label}</span>
    </span>
  );
}

export function BenefitWiseWorkspace() {
  const { profile } = useEmployeeSession();
  const [, setThreadId] = useQueryState("threadId");
  if (!profile) return null;

  return (
    <main className="chat-shell">
      <header className="chat-header">
        <button
          className="chat-brand"
          type="button"
          onClick={() => setThreadId(null)}
          aria-label="Start a new BenefitWise conversation"
        >
          <BenefitWiseLogo className="chat-brand-mark" priority />
          <span>BenefitWise</span>
        </button>

        <div className="chat-header-actions">
          <GraphStatus />
          <Link
            className="icon-button"
            href="/history"
            aria-label="Chat history"
            title="Chat history"
          >
            <History aria-hidden="true" className="size-5" />
          </Link>
          <button
            className="icon-button"
            type="button"
            onClick={() => setThreadId(null)}
            aria-label="New conversation"
            title="New conversation"
          >
            <SquarePen aria-hidden="true" className="size-5" />
          </button>
          <EmployeeProfileMenu />
        </div>
      </header>
      <Thread />
    </main>
  );
}
