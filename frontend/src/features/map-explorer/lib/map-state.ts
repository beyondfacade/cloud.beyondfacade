import type { MapMetricKey, MetricAxis } from "@/shared/api/types";
import { INDUSTRIES, type IndustryId } from "@/shared/industries";
import { isQuarter } from "./quarters";

/** 컨트롤바의 두 무리 — 무리 자체가 모드다. 동네 무리를 고르면 업종·연도 셀렉터가 흐려지고 분기 셀렉터가 산다.
 *  명시적 모드 토글을 두지 않는다. 어느 무리에 있느냐가 지표의 축(`axis`)이고, METRIC_SOURCES의 axis와
 *  같아야 한다(테스트로 고정). 동네 무리 4종 외 파생 지표는 API에만 있고 버튼이 없다 — 지도는 "어디"를
 *  고르는 도구고 근거 수치는 패널 몫이다(무대 설계서 §2). */
export const METRIC_GROUPS = [
  {
    key: "region",
    label: "동네",
    axis: "region_quarter",
    metrics: ["neighborhood_type", "night_index", "fnb_share", "operating_months"],
  },
  {
    key: "industry",
    label: "업종",
    axis: "industry_year",
    metrics: ["closure_rate", "growth_rate", "store_count"],
  },
] as const satisfies readonly { key: string; label: string; axis: MetricAxis; metrics: readonly MapMetricKey[] }[];

export type MetricGroup = (typeof METRIC_GROUPS)[number];

/** 평면 순회용 — 그룹에서 파생한다. 순서는 컨트롤바 순서와 같다. */
export const METRICS = METRIC_GROUPS.flatMap((g) => g.metrics) as readonly MapMetricKey[];

export function metricGroupOf(metric: MapMetricKey): MetricGroup {
  const group = METRIC_GROUPS.find((g) => (g.metrics as readonly MapMetricKey[]).includes(metric));
  if (!group) throw new Error(`무리에 속하지 않은 지표: ${metric}`);
  return group;
}

export const YEARS = Array.from({ length: 8 }, (_, i) => 2019 + i);

/** 화면 표기용 한국어 라벨. URL 파라미터·API 값은 영문 id를 그대로 쓴다. */
export const METRIC_LABELS: Record<MapMetricKey, string> = {
  neighborhood_type: "동네 유형",
  night_index: "심야 체류",
  fnb_share: "음식·유흥 비중",
  operating_months: "영업 지속 개월",
  closure_rate: "폐업률",
  growth_rate: "성장률",
  store_count: "점포수",
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
  /** 동×분기 지표의 시점. null = 최신(백엔드가 고른다). 업종 지표의 `year`와 따로 둔다 —
   *  연 데이터를 분기로 위장하지 않고, 무리를 오가도 각자의 시점이 유지된다. */
  year_quarter: string | null;
  region: string | null;
  /** 관문에서 온 예산(원). 지도는 소비하지 않지만 실어두지 않으면 첫 상태 변경 때 URL에서 사라진다 — T3 프리필 원천. */
  budget: number | null;
}

// 기본 지표는 동네 유형이다 — 창업자가 처음 묻는 건 "어디가 망하나"가 아니라 "어디가 어떤 곳이냐"다.
// 관문(T1)이 동 선택 상태로 내려놓을 때도 지도는 유형으로 색칠돼 있어야 패널 서사와 이어진다.
export const DEFAULT_STATE: MapState = {
  industry: "cafe",
  metric: "neighborhood_type",
  year: 2026,
  year_quarter: null,
  region: null,
  budget: null,
};

export function serializeMapState(state: MapState): string {
  const params = new URLSearchParams();
  params.set("industry", state.industry);
  params.set("metric", state.metric);
  params.set("year", String(state.year));
  if (state.year_quarter) {
    params.set("year_quarter", state.year_quarter);
  }
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
  const yearQuarter = sp.get("year_quarter");
  const region = sp.get("region");
  const budget = Number(sp.get("budget"));

  return {
    industry: INDUSTRIES.includes(industry as IndustryId) ? industry! : DEFAULT_STATE.industry,
    metric: METRICS.includes(metric as MapMetricKey) ? (metric as MapMetricKey) : DEFAULT_STATE.metric,
    year: YEARS.includes(Number(year)) ? Number(year) : DEFAULT_STATE.year,
    year_quarter: isQuarter(yearQuarter) ? yearQuarter : null,
    region: region || null,
    budget: Number.isInteger(budget) && budget > 0 ? budget : null,
  };
}
