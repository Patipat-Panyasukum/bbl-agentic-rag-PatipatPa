"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useEmployeeSession } from "@/providers/EmployeeSession";
import { ProfileAvatar } from "./profile-avatar";

export function EmployeeProfileMenu() {
  const router = useRouter();
  const { profile, signOut } = useEmployeeSession();
  const [open, setOpen] = useState(false);
  if (!profile) return null;

  const fields = [
    ["Employee ID", profile.employeeId],
    ["Job level", profile.jobLevel],
    ["Country", profile.country],
    ["Company", profile.company],
    ["Type", profile.employeeType],
  ];

  return (
    <div className="employee-profile" data-open={open}>
      <button
        className="employee-profile-trigger"
        type="button"
        aria-label={`Employee profile ${profile.employeeId}`}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <ProfileAvatar profile={profile} size="header" />
      </button>
      <div className="employee-profile-card">
        <div className="employee-profile-card-heading">
          <ProfileAvatar profile={profile} size="card" />
          <strong>Demo employee</strong>
          <small>Resolved from local SQLite</small>
        </div>
        <dl>
          {fields.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <button
          type="button"
          onClick={() => {
            signOut();
            router.replace("/");
          }}
        >
          <LogOut aria-hidden="true" className="size-4" />
          Change demo profile
        </button>
      </div>
    </div>
  );
}
