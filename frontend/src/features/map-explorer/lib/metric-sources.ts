import type {
  CategoryRow,
  CommerceChangeMetricKey,
  MapMetricKey,
  MetricAxis,
  MetricKey,
  MetricRow,
  ProfileMetricKey,
} from "@/shared/api/types";
import { fetchCommerceChangeMetrics, fetchMetrics, fetchProfileMetrics, fetchProfileTypes } from "../api";
import type { ColorScheme } from "./metric-color";

/** 한 번의 지도 조회가 아는 것 전부. 원천은 자기 축의 값만 쓴다 — 업종×연도 원천은 yearQuarter를,
 *  동×분기 원천은 industry·year를 무시한다. 무시하는 값을 질의 키에 넣으면 같은 응답을 중복 캐싱한다. */
export interface MetricQuery {
  industry: string;
  year: number;
  /** null = 최신 분기(백엔드가 고른다). */
  yearQuarter: string | null;
}

/** 숫자 지표 — {region_code, value}. 분위수·발산 스케일과 값 구간 범례의 대상. */
export interface NumericMetricSource {
  kind: "numeric";
  axis: MetricAxis;
  scheme: ColorScheme;
  queryKey: (query: MetricQuery) => unknown[];
  fetch: (query: MetricQuery) => Promise<MetricRow[]>;
}

/** 범주 지표 — {region_code, type_code}. 범주 팔레트와 이름 범례의 대상.
 *  한 타입에 value/category를 섞어 한쪽을 null로 두지 않는다 — 판별 합집합으로 나눈다. */
export interface CategoricalMetricSource {
  kind: "categorical";
  axis: MetricAxis;
  queryKey: (query: MetricQuery) => unknown[];
  fetch: (query: MetricQuery) => Promise<CategoryRow[]>;
}

export type MetricSource = NumericMetricSource | CategoricalMetricSource;

/** 업종×연도 지표 — region_industry_metric (GET /metrics). */
function industryMetric(metric: MetricKey, scheme: ColorScheme): NumericMetricSource {
  return {
    kind: "numeric",
    axis: "industry_year",
    scheme,
    queryKey: ({ industry, year }) => ["metrics", metric, industry, year],
    fetch: ({ industry, year }) => fetchMetrics(industry, metric, year),
  };
}

/** 동×분기 파생 지표 — region_profile_quarter (GET /profiles?metric=). */
function profileMetric(metric: ProfileMetricKey, scheme: ColorScheme): NumericMetricSource {
  return {
    kind: "numeric",
    axis: "region_quarter",
    scheme,
    queryKey: ({ yearQuarter }) => ["profile-metrics", metric, yearQuarter],
    fetch: ({ yearQuarter }) => fetchProfileMetrics(metric, yearQuarter ?? undefined),
  };
}

/** 동×분기 상권 변화 지표 — region_commerce_change (GET /commerce-changes). */
function commerceChangeMetric(metric: CommerceChangeMetricKey, scheme: ColorScheme): NumericMetricSource {
  return {
    kind: "numeric",
    axis: "region_quarter",
    scheme,
    queryKey: ({ yearQuarter }) => ["commerce-change-metrics", metric, yearQuarter],
    fetch: ({ yearQuarter }) => fetchCommerceChangeMetrics(metric, yearQuarter ?? undefined),
  };
}

/** 지표 → 원천 (GoF Strategy 테이블). 원천이 넷으로 갈리지만 호출하는 쪽은 분기하지 않는다 —
 *  `kind`로 스케일·범례가, `axis`로 셀렉터가 갈리고, 색 스킴도 여기서 함께 선언해 지표당 아는 자리를 줄인다. */
export const METRIC_SOURCES: Record<MapMetricKey, MetricSource> = {
  neighborhood_type: {
    kind: "categorical",
    axis: "region_quarter",
    queryKey: ({ yearQuarter }) => ["profile-types", yearQuarter],
    fetch: ({ yearQuarter }) => fetchProfileTypes(yearQuarter ?? undefined),
  },
  // 1.0 = 하루 평균. 높을수록 밤에 사람이 머문다 — 한 방향 척도
  night_index: profileMetric("night_index", "sequential"),
  fnb_share: profileMetric("fnb_share", "sequential"),
  // 길게 버티는 쪽이 좋다는 한 방향 척도라 발산형이 아니다
  operating_months: commerceChangeMetric("operating_months", "sequential"),
  closure_rate: industryMetric("closure_rate", "sequential"),
  growth_rate: industryMetric("growth_rate", "diverging"),
  store_count: industryMetric("store_count", "sequential"),
};
