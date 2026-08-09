"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { type DemoProfile, getDemoProfile } from "@/lib/demo-profiles";

const STORAGE_KEY = "benefitwise:demo-employee";

type EmployeeSessionValue = {
  profile: DemoProfile | null;
  ready: boolean;
  signIn: (employeeId: string) => void;
  signOut: () => void;
};

const EmployeeSessionContext = createContext<EmployeeSessionValue | null>(null);

export function EmployeeSessionProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<DemoProfile | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // The browser value selects a fictional demo profile; the server still
    // resolves the authoritative context from SQLite on every graph run.
    const restored = getDemoProfile(window.localStorage.getItem(STORAGE_KEY));
    setProfile(restored);
    setReady(true);
  }, []);

  const signIn = useCallback((employeeId: string) => {
    const selected = getDemoProfile(employeeId);
    if (!selected) throw new Error("Unknown demo employee profile");
    window.localStorage.setItem(STORAGE_KEY, selected.employeeId);
    setProfile(selected);
  }, []);

  const signOut = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setProfile(null);
  }, []);

  const value = useMemo(
    () => ({ profile, ready, signIn, signOut }),
    [profile, ready, signIn, signOut],
  );

  return (
    <EmployeeSessionContext.Provider value={value}>
      {children}
    </EmployeeSessionContext.Provider>
  );
}

export function useEmployeeSession(): EmployeeSessionValue {
  const value = useContext(EmployeeSessionContext);
  if (!value) {
    throw new Error(
      "useEmployeeSession must be used within EmployeeSessionProvider",
    );
  }
  return value;
}
