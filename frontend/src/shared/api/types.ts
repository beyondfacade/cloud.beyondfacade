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

/** 어린이집 지도 마커 — 운영 중·좌표 보유 시설 + 최신 현황 (GET /childcare-centers?region=). */
export interface ChildcareCenter {
  center_id: string;
  name: string;
  type_name: string;
  status_name: string | null; // 원천 공란 null
  lat: number;
  lng: number;
  base_date: string;
  capacity: number;
  child_count: number;
  waiting_count: number | null; // 원천 공란 null — 0으로 추정하지 않음
}

/** 행정동 어린이집 요약 (GET /childcare-center-stats/summary?region=). */
export interface ChildcareRegionSummary {
  region_code: string;
  base_date: string | null;
  center_count: number;
  capacity: number;
  child_count: number;
  occupancy_rate: number | null; // 현원/정원 — 정원 0이면 null
  waiting_count: number | null; // 입소대기 합(중복 신청 포함) — 전 시설 공란이면 null
}

/** 편의점 지도 마커 — 좌표 보유 현행 편의점 (GET /convenience-stores?region=). */
export interface ConvenienceStore {
  store_id: string;
  name: string;
  branch_name: string | null;
  brand: string | null; // 상호 기반 추출 — 미확인 null
  lat: number;
  lng: number;
  road_address: string | null;
}

/** 행정동 편의점 요약 (GET /convenience-stores/summary?region=). */
export interface ConvenienceRegionSummary {
  region_code: string;
  store_count: number;
  brands: { brand: string | null; count: number }[]; // 건수 내림차순, 미확인(null)은 맨 뒤
  source_stdr_ym: string | null; // 원천 기준연월 YYYYMM
}
