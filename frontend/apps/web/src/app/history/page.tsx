"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChatHistory } from "@/components/history/chat-history";
import { Toaster } from "@/components/ui/sonner";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import { ThreadProvider } from "@/providers/Thread";

function ProtectedHistory() {
  const router = useRouter();
  const { profile, ready } = useEmployeeSession();

  useEffect(() => {
    if (ready && !profile) router.replace("/");
  }, [profile, ready, router]);

  if (!ready || !profile) {
    return (
      <main className="grid min-h-dvh place-items-center bg-background">
        <p className="animate-pulse text-sm text-muted-foreground">
          Resolving demo profile...
        </p>
      </main>
    );
  }

  return (
    <ThreadProvider>
      <ChatHistory />
    </ThreadProvider>
  );
}

export default function HistoryPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-dvh place-items-center bg-background">
          <p className="animate-pulse text-sm text-muted-foreground">
            Opening saved conversations...
          </p>
        </main>
      }
    >
      <Toaster />
      <ProtectedHistory />
    </Suspense>
  );
}
