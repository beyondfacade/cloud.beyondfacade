import type { AgentEvent, AgentName, Citation, ReportFacts, ReportSection } from "@/shared/api/types";

export type AgentStatus = "idle" | "running" | "done" | "error";

export interface AgentToolCall {
  tool: string;
  summary: string;
}

export interface AgentSlot {
  status: AgentStatus;
  tools: AgentToolCall[];
}

export interface AgentState {
  agents: Record<AgentName, AgentSlot>;
  facts: ReportFacts | null;
  sections: Partial<Record<ReportSection, string>>;
  done: boolean;
  citations: Citation[];
  error: string | null;
}

const AGENT_NAMES: AgentName[] = ["orchestrator", "facts", "writer", "market", "shock", "funding"];

export function initialAgentState(): AgentState {
  const agents = {} as Record<AgentName, AgentSlot>;
  for (const name of AGENT_NAMES) {
    agents[name] = { status: "idle", tools: [] };
  }
  return { agents, facts: null, sections: {}, done: false, citations: [], error: null };
}

export function applyAgentEvent(state: AgentState, ev: AgentEvent): AgentState {
  switch (ev.type) {
    case "agent_status":
      return {
        ...state,
        agents: {
          ...state.agents,
          [ev.agent]: { ...state.agents[ev.agent], status: ev.status },
        },
      };
    case "tool_call":
      return {
        ...state,
        agents: {
          ...state.agents,
          [ev.agent]: {
            ...state.agents[ev.agent],
            tools: [...state.agents[ev.agent].tools, { tool: ev.tool, summary: ev.summary }],
          },
        },
      };
    case "facts":
      return { ...state, facts: ev.facts };
    case "report_delta":
      return {
        ...state,
        sections: {
          ...state.sections,
          [ev.section]: (state.sections[ev.section] ?? "") + ev.markdown,
        },
      };
    case "report_done":
      return { ...state, done: true, citations: ev.citations };
    default:
      return state;
  }
}
