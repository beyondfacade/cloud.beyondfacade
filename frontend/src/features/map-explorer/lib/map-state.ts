import type { MetricKey } from "@/shared/api/types";

export const INDUSTRIES = [
  "cafe",
  "convenience_store",
  "hair_salon",
  "karaoke",
  "pc_bang",
  "gym",
  "billiard",
  "real_estate",
  "academy",
  "childcare",
] as const;

export const METRICS = ["closure_rate", "growth_rate", "store_count"] as const;

export const YEARS = Array.from({ length: 8 }, (_, i) => 2019 + i);

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
  const industry = sp.get("industry");
  const metric = sp.get("metric");
  const year = sp.get("year");
  const region = sp.get("region");

  return {
    industry: INDUSTRIES.includes(industry as any) ? industry! : DEFAULT_STATE.industry,
    metric: METRICS.includes(metric as any) ? (metric as MetricKey) : DEFAULT_STATE.metric,
    year: YEARS.includes(Number(year)) ? Number(year) : DEFAULT_STATE.year,
    region: region || null,
  };
}
