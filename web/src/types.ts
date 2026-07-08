export interface ClientSummary {
  id: string;
  name: string;
  meetingCount: number;
  lastMeeting: string | null;
  netWorth: number | null;
}

export interface MeetingBrief {
  id: string;
  timestamp: string;
  summary: string;
}

export interface Account {
  name: string;
  type?: string;
  balance?: number;
}

export interface ClientDetail {
  id: string;
  name: string;
  profile: Record<string, unknown>;
  financials: {
    accounts?: Account[];
    other_assets?: { name: string; value?: number }[];
    liabilities?: { name: string; balance?: number }[];
    income?: { source: string; annual?: number }[];
    goals?: { goal: string; target?: string }[];
    risk_tolerance?: string;
  } | null;
  netWorth: number | null;
  meetings: MeetingBrief[];
}

export interface Meeting {
  id: string;
  _timestamp: string;
  notes: string;
  summary: string;
  action_items: string;
  flags: string;
  email: string;
  accuracy?: { accuracy: number | null };
}

export interface AgentStep {
  type: "thought" | "action";
  text?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: string;
}

export interface AgentResult {
  answer: string;
  steps: AgentStep[];
}

export interface PanelResult {
  reasoning: string;
  selected: string[];
  available: Record<string, string>;
  round1: { key: string; label: string; text: string }[];
  cross: { key: string; label: string; text: string }[];
  synthesis: string;
}
