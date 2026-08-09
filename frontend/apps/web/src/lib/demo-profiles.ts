export type DemoProfile = {
  employeeId: string;
  jobLevel: string;
  country: string;
  company: string;
  employeeType: string;
  descriptor: string;
  avatarSrc: string;
};

// These fictional profiles mirror the deterministic SQLite seed exactly.
export const DEMO_PROFILES: readonly DemoProfile[] = [
  {
    employeeId: "E001",
    jobLevel: "JL3",
    country: "TH",
    company: "DEMO",
    employeeType: "General",
    descriptor: "General employee",
    avatarSrc: "/avatars/e001.png",
  },
  {
    employeeId: "E002",
    jobLevel: "JL6",
    country: "TH",
    company: "DEMO",
    employeeType: "General",
    descriptor: "Senior general employee",
    avatarSrc: "/avatars/e002.png",
  },
  {
    employeeId: "E003",
    jobLevel: "JL1",
    country: "TH",
    company: "DEMO",
    employeeType: "Operations",
    descriptor: "Operations employee",
    avatarSrc: "/avatars/e003.png",
  },
];

export function getDemoProfile(employeeId: string | null): DemoProfile | null {
  if (!employeeId) return null;
  return (
    DEMO_PROFILES.find((profile) => profile.employeeId === employeeId) ?? null
  );
}
