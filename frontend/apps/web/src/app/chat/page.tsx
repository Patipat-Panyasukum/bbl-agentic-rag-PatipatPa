"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import { BenefitWiseWorkspace } from "@/components/benefitwise/workspace";
import { Toaster } from "@/components/ui/sonner";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import { StreamProvider } from "@/providers/Stream";
import { ThreadProvider } from "@/providers/Thread";

function ProtectedWorkspace() {
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
      <StreamProvider>
        <BenefitWiseWorkspace />
      </StreamProvider>
    </ThreadProvider>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-dvh place-items-center bg-background">
          <p className="animate-pulse text-sm text-muted-foreground">
            Opening conversation...
          </p>
        </main>
      }
    >
      <Toaster />
      <ProtectedWorkspace />
    </Suspense>
  );
}
