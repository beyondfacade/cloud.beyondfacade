export type AgentName = "orchestrator" | "market" | "shock" | "funding";

export type AgentEvent =
  | { type: "agent_status"; agent: AgentName; status: "running" | "done" | "error" }
  | { type: "tool_call"; agent: AgentName; tool: string; summary: string }
  | { type: "report_delta"; section: string; markdown: string }
  | { type: "report_done"; report_id: string; citations: unknown[] };

export type MetricKey = "closure_rate" | "growth_rate" | "store_count";

export interface MetricRow {
  region_code: string;
  value: number;
}

export interface SummaryCard {
  label: string;
  value: string;
  grade: "fact" | "signal";
}

export interface RegionSummary {
  region_code: string;
  name: string;
  industry_id: string;
  cards: SummaryCard[];
}

export interface Store {
  store_id: string;
  name: string;
  lat: number;
  lng: number;
  status_name: string;
  open_date: string;
}
