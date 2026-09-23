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

/** 행정동 동네 프로필 (GET /profiles/{region_code}?year_quarter=). 분기를 생략하면 최신 분기.
 *  유형·시간대는 **코드**다 — 화면 문구는 @/shared/neighborhood이 갖는다.
 *  `type_reason`만 예외로 한국어인데 실제로 넘은 수치가 박힌 문장이라 표현이 아니라 데이터다. */
export interface RegionProfile {
  region_code: string;
  year_quarter: string; // '20262'
  neighborhood_type: string; // office | campus | dining | hub | residential | mixed
  type_reason: string;
  time_label: string | null; // morning | day | evening | night | flat
  peak_block: string | null; // morning | day | evening | night
  trough_block: string | null;
  worker_resident_ratio: number | null; // 직장인구 결측 11개 동은 null — 0으로 읽지 말 것
  weekend_index: number | null; // 주말 일평균 ÷ 평일 일평균
  night_index: number | null; // 00~06 시간당 강도, 1.0 = 24시간 균등
  footfall_20s_share: number | null;
  fnb_share: number | null; // 음식+유흥 결제 비중
  facility_total: number | null;
  resident_total: number | null;
}
