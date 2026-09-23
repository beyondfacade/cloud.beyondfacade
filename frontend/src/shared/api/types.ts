export type AgentName = "orchestrator" | "market" | "shock" | "funding";

export type AgentEvent =
  | { type: "agent_status"; agent: AgentName; status: "running" | "done" | "error" }
  | { type: "tool_call"; agent: AgentName; tool: string; summary: string }
  | { type: "report_delta"; section: string; markdown: string }
  | { type: "report_done"; report_id: string; citations: unknown[] };

export type MetricKey = "closure_rate" | "growth_rate" | "store_count";

/** GET /profiles?metric= 가 지도에 올리는 파생 지표 (동×분기 숫자, v0.30.0의 7종 중 화면에 노출하는 둘). */
export type ProfileMetricKey = "night_index" | "fnb_share";

/** GET /commerce-changes 가 지원하는 지표 (동×분기 숫자). */
export type CommerceChangeMetricKey = "operating_months";

/** 업종 축이 없는 동 단위 분기 지표. 업종을 바꿔도 값이 같다.
 *  operating_months → /commerce-changes, night_index·fnb_share → /profiles?metric= (숫자), neighborhood_type → /profiles/types (범주). */
export type RegionMetricKey = CommerceChangeMetricKey | ProfileMetricKey | "neighborhood_type";

/** 숫자 계약({region_code, value})으로 오는 지표. 범례 값 표기·분위수 스케일의 대상. */
export type NumericMetricKey = MetricKey | CommerceChangeMetricKey | ProfileMetricKey;

/** 범주 계약({region_code, type_code})으로 오는 지표. 숫자 계약과 경로가 다르다 (map-metric-contract §5). */
export type CategoricalMetricKey = "neighborhood_type";

/** 지도 단계구분도가 그릴 수 있는 전체 지표. 원천은 넷으로 갈리지만 호출하는 쪽은 METRIC_SOURCES 한 곳만 안다. */
export type MapMetricKey = MetricKey | RegionMetricKey;

/** 지표의 축 — 셀렉터가 이 값을 정직하게 따라간다. 업종×연도 지표에 분기를, 동×분기 지표에 업종을 묻지 않는다. */
export type MetricAxis = "industry_year" | "region_quarter";

export interface MetricRow {
  region_code: string;
  value: number;
}

/** 범주 단계구분도 행 (GET /profiles/types). 한 타입에 value/category를 섞어 null로 두지 않는다. */
export interface CategoryRow {
  region_code: string;
  type_code: string; // office | campus | dining | hub | residential | mixed
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
  /** 4블록 시간당 강도(1.0 = 24시간 균등). 배치가 계산한 값 — 화면은 보정을 다시 하지 않는다. 넷 중 하나라도 없으면 null. */
  block_intensities: BlockIntensities | null;
}

export interface BlockIntensities {
  morning: number;
  day: number;
  evening: number;
  night: number;
}

/** 같은 분기의 서울 전체 평균 — 동의 값 옆에 놓는 비교 기준 (GET /commerce-changes/{region_code}). */
export interface SeoulCommerceBaseline {
  operating_months: number | null;
  closed_months: number | null;
}

/** 동별 상권 변화 상세 (GET /commerce-changes/{region_code}?year_quarter=). 분기 생략 시 최신. */
export interface RegionCommerceChangeDetail {
  region_code: string;
  year_quarter: string;
  change_code: string | null; // HH | HL | LH | LL
  change_name: string | null; // 정체 | 상권축소 | 상권확장 | 다이나믹
  operating_months: number | null; // 운영 영업 개월 평균
  closed_months: number | null; // 폐업 영업 개월 평균
  seoul: SeoulCommerceBaseline | null; // baseline 행이 없는 분기면 null
}

/** 시간대 6구간 중 하나 — 두 강도 모두 시간당 보정값(1.0 = 24시간 균등), gap = sales − footfall. */
export interface HourGapBand {
  hour_band: string; // 00_06 | 06_11 | 11_14 | 14_17 | 17_21 | 21_24
  footfall_intensity: number;
  sales_intensity: number;
  gap: number;
}

/** 동×업종×분기 시간대 어긋남 (GET /hour-gaps?region=&industry=). 매출 원천이 20254까지라 프로필과 최신 분기가 다르다. */
export interface RegionIndustryHourGap {
  region_code: string;
  industry_id: string;
  year_quarter: string;
  bands: HourGapBand[];
}

/** 관문 되묻기 후보 — "역삼동"처럼 사람이 말하는 이름이 번호 동 여럿으로 갈라질 때 (POST /intent). */
export interface IntentCandidate {
  region_code: string;
  region_name: string;
  district_code: string;
  district_name: string;
}

/** 한 줄 진단 — LLM이 아니라 어휘 테이블로 조립된 결정론 문장. peak는 gap이 아니라 매출 강도 최대 구간. */
export interface IntentDiagnosis {
  type_code: string;
  type_name: string;
  time_label: string | null;
  peak_sales_band: string | null;
  sentence: string;
  year_quarter: string;
  hour_gap_quarter: string | null;
}

/** POST /intent 응답. A 동+업종 · B 동만 · C 동 없음. `source`는 어느 경로가 채웠나(rule|llm). */
export interface IntentResult {
  intent_type: "A" | "B" | "C";
  region_code: string | null;
  region_name: string | null;
  district_code: string | null;
  industry_id: string | null;
  budget_krw: number | null;
  missing: ("region" | "industry" | "budget")[];
  candidates: IntentCandidate[];
  diagnosis: IntentDiagnosis | null;
  source: "rule" | "llm";
}
