import type { CategoryRow } from "@/shared/api/types";
import { isVerdictIndustry, VERDICT_CODES, verdictLabel } from "@/shared/verdict";
import { fetchVerdictMetrics } from "../api";
import { verdictPalette, type MapTheme } from "./verdict-palette";

export interface MetricQuery {
  industry: string;
}

/** 최신 판정 원천 — 지도와 범례가 팔레트·순서·라벨을 공유한다. */
export interface CategoricalMetricSource {
  axis: "industry_latest";
  queryKey: (query: MetricQuery) => unknown[];
  fetch: (query: MetricQuery) => Promise<CategoryRow[]>;
  palette: (theme: MapTheme) => Record<string, string>;
  order: readonly string[];
  labelOf: (code: string) => { name: string; qualifier: string };
}

export const METRIC_SOURCES: { verdict: CategoricalMetricSource } = {
  verdict: {
    axis: "industry_latest",
    queryKey: ({ industry }) => ["verdicts", industry],
    fetch: ({ industry }) => fetchVerdictMetrics(industry),
    palette: verdictPalette,
    order: VERDICT_CODES,
    labelOf: verdictLabel,
  },
};

/** 판정 제외 업종은 조회를 끄고 준비 중 안내를 표시한다. */
export function isVerdictMissingForIndustry(industry: string): boolean {
  return !isVerdictIndustry(industry);
}
