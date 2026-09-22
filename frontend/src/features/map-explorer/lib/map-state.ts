import type { MetricKey } from "@/shared/api/types";
import { INDUSTRIES, type IndustryId } from "@/shared/industries";

export const METRICS = ["closure_rate", "growth_rate", "store_count"] as const;

export const YEARS = Array.from({ length: 8 }, (_, i) => 2019 + i);

/** 화면 표기용 한국어 라벨. URL 파라미터·API 값은 영문 id를 그대로 쓴다. */
export const METRIC_LABELS: Record<(typeof METRICS)[number], string> = {
  closure_rate: "폐업률",
  growth_rate: "성장률",
  store_count: "점포수",
};

/**
 * 스냅샷 원천 업종 — 개폐업 이력이 없어 폐업률·성장률이 NULL.
 * 지도 코로플레스·컨트롤은 점포수만 노출한다 (HANDOFF §2-3).
 */
export const SNAPSHOT_INDUSTRIES = new Set<IndustryId>(["childcare", "convenience_store"]);

export function metricsForIndustry(industry: string): readonly MetricKey[] {
  if (SNAPSHOT_INDUSTRIES.has(industry as IndustryId)) {
    return ["store_count"];
  }
  return METRICS;
}

/** 업종에 없는 지표면 store_count(스냅샷) 또는 기본 폐업률로 보정. */
export function coerceMetric(industry: string, metric: MetricKey): MetricKey {
  const allowed = metricsForIndustry(industry);
  return allowed.includes(metric) ? metric : allowed[0];
}

export interface MapState {
  industry: string;
  metric: MetricKey;
  year: number;
  region: string | null;
}

export const DEFAULT_STATE: MapState = {
  industry: "cafe",
  metric: "closure_rate",
  year: 2026,
  region: null,
};

export function serializeMapState(state: MapState): string {
  const params = new URLSearchParams();
  params.set("industry", state.industry);
  params.set("metric", state.metric);
  params.set("year", String(state.year));
  if (state.region) {
    params.set("region", state.region);
  }
  return params.toString();
}

export function parseMapState(sp: URLSearchParams): MapState {
  const industryRaw = sp.get("industry");
  const industry = INDUSTRIES.includes(industryRaw as IndustryId)
    ? industryRaw!
    : DEFAULT_STATE.industry;
  const metricRaw = sp.get("metric");
  const metric = METRICS.includes(metricRaw as MetricKey)
    ? (metricRaw as MetricKey)
    : DEFAULT_STATE.metric;
  const year = sp.get("year");
  const region = sp.get("region");

  return {
    industry,
    metric: coerceMetric(industry, metric),
    year: YEARS.includes(Number(year)) ? Number(year) : DEFAULT_STATE.year,
    region: region || null,
  };
}
