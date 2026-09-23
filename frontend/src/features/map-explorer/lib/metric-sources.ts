import type { CategoryRow, MapMetricKey, MetricKey, MetricRow } from "@/shared/api/types";
import { fetchCommerceChangeMetrics, fetchMetrics, fetchProfileTypes } from "../api";
import type { ColorScheme } from "./metric-color";

/** 숫자 지표 — {region_code, value}. 분위수·발산 스케일과 값 구간 범례의 대상. */
export interface NumericMetricSource {
  kind: "numeric";
  scheme: ColorScheme;
  queryKey: (industry: string, year: number) => unknown[];
  fetch: (industry: string, year: number) => Promise<MetricRow[]>;
}

/** 범주 지표 — {region_code, type_code}. 범주 팔레트와 이름 범례의 대상.
 *  한 타입에 value/category를 섞어 한쪽을 null로 두지 않는다 — 판별 합집합으로 나눈다. */
export interface CategoricalMetricSource {
  kind: "categorical";
  queryKey: (industry: string, year: number) => unknown[];
  fetch: (industry: string, year: number) => Promise<CategoryRow[]>;
}

export type MetricSource = NumericMetricSource | CategoricalMetricSource;

/** 업종×연도 지표 — region_industry_metric (GET /metrics). */
function industryMetric(metric: MetricKey, scheme: ColorScheme): NumericMetricSource {
  return {
    kind: "numeric",
    scheme,
    queryKey: (industry, year) => ["metrics", metric, industry, year],
    fetch: (industry, year) => fetchMetrics(industry, metric, year),
  };
}

/** 지표 → 원천 (GoF Strategy 테이블). 원천이 셋으로 갈리지만 호출하는 쪽은 분기하지 않는다 —
 *  `kind`로 스케일·범례가 갈리고, 색 스킴도 여기서 함께 선언해 지표당 아는 자리를 하나 줄인다. */
export const METRIC_SOURCES: Record<MapMetricKey, MetricSource> = {
  neighborhood_type: {
    kind: "categorical",
    // 업종·연도가 값에 영향을 주지 않는다. 질의 키에 넣으면 같은 응답을 업종 수만큼 중복 캐싱한다
    queryKey: () => ["profile-types"],
    fetch: () => fetchProfileTypes(),
  },
  closure_rate: industryMetric("closure_rate", "sequential"),
  growth_rate: industryMetric("growth_rate", "diverging"),
  store_count: industryMetric("store_count", "sequential"),
  operating_months: {
    kind: "numeric",
    // 길게 버티는 쪽이 좋다는 한 방향 척도라 발산형이 아니다
    scheme: "sequential",
    queryKey: () => ["commerce-change-metrics", "operating_months"],
    fetch: () => fetchCommerceChangeMetrics("operating_months"),
  },
};
