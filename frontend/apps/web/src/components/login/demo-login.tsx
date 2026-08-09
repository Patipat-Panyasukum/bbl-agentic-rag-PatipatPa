"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Check } from "lucide-react";
import { DEMO_PROFILES } from "@/lib/demo-profiles";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import { Button } from "@/components/ui/button";
import { BenefitWiseLogo } from "@/components/brand/benefitwise-logo";
import { ProfileAvatar } from "@/components/employee/profile-avatar";

export function DemoLogin() {
  const router = useRouter();
  const { ready, signIn } = useEmployeeSession();
  const [selectedId, setSelectedId] = useState("E001");

  if (!ready) {
    return (
      <main className="grid min-h-dvh place-items-center bg-background">
        <p className="text-sm text-muted-foreground">Preparing demo...</p>
      </main>
    );
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="profile-heading">
        <BenefitWiseLogo className="login-brand-mark" priority />
        <div className="text-center">
          <p className="mb-2 text-sm font-medium text-muted-foreground">
            BenefitWise · Local demo
          </p>
          <h1 id="profile-heading" className="text-2xl font-semibold">
            Select a demo profile
          </h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Choose a fictional employee context before starting the chat.
          </p>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            signIn(selectedId);
            router.push("/chat");
          }}
        >
          <fieldset className="profile-list">
            <legend className="sr-only">Available employee profiles</legend>
            {DEMO_PROFILES.map((candidate) => {
              const selected = candidate.employeeId === selectedId;
              return (
                <label
                  key={candidate.employeeId}
                  className="profile-row"
                  data-selected={selected}
                >
                  <input
                    className="sr-only"
                    type="radio"
                    name="employee"
                    value={candidate.employeeId}
                    checked={selected}
                    onChange={() => setSelectedId(candidate.employeeId)}
                  />
                  <ProfileAvatar profile={candidate} size="login" />
                  <span className="min-w-0 flex-1">
                    <strong className="block text-sm">
                      {candidate.employeeId} · {candidate.descriptor}
                    </strong>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {candidate.jobLevel} · {candidate.employeeType} ·{" "}
                      {candidate.country}
                    </span>
                  </span>
                  <span className="profile-check" aria-hidden="true">
                    {selected && <Check className="size-3.5" strokeWidth={3} />}
                  </span>
                </label>
              );
            })}
          </fieldset>

          <Button className="mt-5 w-full" size="lg" type="submit">
            Enter as {selectedId}
            <ArrowRight aria-hidden="true" className="size-4" />
          </Button>
        </form>

        <p className="text-center text-xs leading-5 text-muted-foreground">
          No password or real employee data is used. This is not production
          authentication.
        </p>
      </section>
    </main>
  );
}
