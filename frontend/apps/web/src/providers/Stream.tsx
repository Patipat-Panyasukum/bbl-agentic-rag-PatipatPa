"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { type Message } from "@langchain/langgraph-sdk";
import { useStream } from "@langchain/langgraph-sdk/react";
import { useQueryState } from "nuqs";
import { toast } from "sonner";
import { useThreads } from "./Thread";

export type EmployeeContextState = {
  employee_id: string;
  job_level: string;
  country: string;
  company: string;
  employee_type: string;
};

export type PolicyEvidenceState = {
  policy_id: string;
  title: string;
  excerpt: string;
  eligibility: Record<string, unknown>;
  similarity_score: number;
  applies_to_current_employee: boolean;
};

export type StateType = {
  messages: Message[];
  employee_id?: string;
  employee_context?: EmployeeContextState;
  retrieval_query?: string;
  evidence?: PolicyEvidenceState[];
  final_answer?: string;
  grounding_valid?: boolean;
};

const useTypedStream = useStream<
  StateType,
  {
    UpdateType: {
      messages?: Message[] | Message | string;
      employee_id?: string;
    };
  }
>;

type ServerStatus = "checking" | "online" | "offline";
type StreamContextType = ReturnType<typeof useTypedStream> & {
  serverStatus: ServerStatus;
};

const StreamContext = createContext<StreamContextType | undefined>(undefined);

const DEFAULT_API_URL = "http://127.0.0.1:2024";
const DEFAULT_ASSISTANT_ID = "benefitwise";

async function checkGraphStatus(apiUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${apiUrl}/info`);
    return response.ok;
  } catch {
    return false;
  }
}

const StreamSession = ({
  children,
  apiUrl,
  assistantId,
}: {
  children: ReactNode;
  apiUrl: string;
  assistantId: string;
}) => {
  const [threadId, setThreadId] = useQueryState("threadId");
  const [serverStatus, setServerStatus] = useState<ServerStatus>("checking");
  const { getThreads, setThreads } = useThreads();

  const streamValue = useTypedStream({
    apiUrl,
    assistantId,
    threadId: threadId ?? null,
    onThreadId: (id) => {
      setThreadId(id);
      window.setTimeout(() => {
        getThreads().then(setThreads).catch(console.error);
      }, 1200);
    },
  });

  useEffect(() => {
    let active = true;
    setServerStatus("checking");
    checkGraphStatus(apiUrl).then((online) => {
      if (!active) return;
      setServerStatus(online ? "online" : "offline");
      if (!online) {
        toast.error("LangGraph server is offline", {
          description: `Start the local graph at ${apiUrl}, then try again.`,
          duration: 10000,
          closeButton: true,
        });
      }
    });
    return () => {
      active = false;
    };
  }, [apiUrl]);

  const contextValue = useMemo(
    () => ({ ...streamValue, serverStatus }),
    [streamValue, serverStatus],
  );

  return (
    <StreamContext.Provider value={contextValue}>
      {children}
    </StreamContext.Provider>
  );
};

export function StreamProvider({ children }: { children: ReactNode }) {
  const envApiUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
  const envAssistantId =
    process.env.NEXT_PUBLIC_ASSISTANT_ID || DEFAULT_ASSISTANT_ID;
  const [apiUrl] = useQueryState("apiUrl", { defaultValue: envApiUrl });
  const [assistantId] = useQueryState("assistantId", {
    defaultValue: envAssistantId,
  });

  return (
    <StreamSession apiUrl={apiUrl} assistantId={assistantId}>
      {children}
    </StreamSession>
  );
}

export function useStreamContext(): StreamContextType {
  const context = useContext(StreamContext);
  if (!context) {
    throw new Error("useStreamContext must be used within StreamProvider");
  }
  return context;
}
