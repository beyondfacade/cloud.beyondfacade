import type { MapMetricKey } from "@/shared/api/types";
import { INDUSTRIES, type IndustryId } from "@/shared/industries";

export const METRICS = ["closure_rate", "growth_rate", "store_count", "operating_months"] as const;

export const YEARS = Array.from({ length: 8 }, (_, i) => 2019 + i);

/** 화면 표기용 한국어 라벨. URL 파라미터·API 값은 영문 id를 그대로 쓴다. */
export const METRIC_LABELS: Record<(typeof METRICS)[number], string> = {
  closure_rate: "폐업률",
  growth_rate: "성장률",
  store_count: "점포수",
  operating_months: "영업 지속 개월",
};

/**
 * 스냅샷 원천 업종 — 개폐업 이력이 없어 폐업률·성장률이 NULL일 수 있음.
 * 지표 UI는 3종 모두 노출하고, 값 없음은 사이드패널·지도 배너로 안내한다.
 */
export const SNAPSHOT_INDUSTRIES = new Set<IndustryId>(["childcare", "convenience_store"]);

export interface MapState {
  industry: string;
  metric: MapMetricKey;
  year: number;
  region: string | null;
  /** 관문에서 온 예산(원). 지도는 소비하지 않지만 실어두지 않으면 첫 상태 변경 때 URL에서 사라진다 — T3 프리필 원천. */
  budget: number | null;
}

export const DEFAULT_STATE: MapState = {
  industry: "cafe",
  metric: "closure_rate",
  year: 2026,
  region: null,
  budget: null,
};

export function serializeMapState(state: MapState): string {
  const params = new URLSearchParams();
  params.set("industry", state.industry);
  params.set("metric", state.metric);
  params.set("year", String(state.year));
  if (state.region) {
    params.set("region", state.region);
  }
  if (state.budget) {
    params.set("budget", String(state.budget));
  }
  return params.toString();
}

export function parseMapState(sp: URLSearchParams): MapState {
  const industry = sp.get("industry");
  const metric = sp.get("metric");
  const year = sp.get("year");
  const region = sp.get("region");
  const budget = Number(sp.get("budget"));

  return {
    industry: INDUSTRIES.includes(industry as IndustryId) ? industry! : DEFAULT_STATE.industry,
    metric: METRICS.includes(metric as MapMetricKey) ? (metric as MapMetricKey) : DEFAULT_STATE.metric,
    year: YEARS.includes(Number(year)) ? Number(year) : DEFAULT_STATE.year,
    region: region || null,
    budget: Number.isInteger(budget) && budget > 0 ? budget : null,
  };
}
