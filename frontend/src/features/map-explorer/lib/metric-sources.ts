import type { MapMetricKey, MetricKey, MetricRow } from "@/shared/api/types";
import { fetchCommerceChangeMetrics, fetchMetrics } from "../api";

/** 지표 하나가 어디서 오는지 — 질의 키와 조회 함수 한 쌍. */
export interface MetricSource {
  queryKey: (industry: string, year: number) => unknown[];
  fetch: (industry: string, year: number) => Promise<MetricRow[]>;
}

/** 업종×연도 지표 — region_industry_metric (GET /metrics). */
function industryMetric(metric: MetricKey): MetricSource {
  return {
    queryKey: (industry, year) => ["metrics", metric, industry, year],
    fetch: (industry, year) => fetchMetrics(industry, metric, year),
  };
}

/** 지표 → 원천 (GoF Strategy 테이블). 원천이 둘로 갈리지만 호출하는 쪽은 분기하지 않는다.
 *  응답 형태가 {region_code, value}로 같아 색 스케일·범례는 그대로 재사용된다. */
export const METRIC_SOURCES: Record<MapMetricKey, MetricSource> = {
  closure_rate: industryMetric("closure_rate"),
  growth_rate: industryMetric("growth_rate"),
  store_count: industryMetric("store_count"),
  operating_months: {
    // 업종·연도가 값에 영향을 주지 않는다. 질의 키에 넣으면 같은 응답을 업종 수만큼 중복 캐싱한다
    queryKey: () => ["commerce-change-metrics", "operating_months"],
    fetch: () => fetchCommerceChangeMetrics("operating_months"),
  },
};
