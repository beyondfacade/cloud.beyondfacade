/** 지표·업종별 데이터 보유 범위 — 셀렉터가 "고를 수는 있지만 빈 지도가 되는" 조합을 제안하지 않게 한다.
 *
 *  `map-metric-contract.md` §6이 세던 "프론트가 지표당 아는 것"의 여섯 번째다. 다섯(목록·라벨·색 스킴·
 *  표기 형식·원천)은 지표만 보면 정해지는데, 보유 범위만은 **(업종, 지표) 쌍**에 걸린다 — 스냅샷 원천
 *  업종은 개폐업 이력이 없어 관측 연도의 점포수 한 칸만 갖는다. 그래서 `METRIC_SOURCES`의 항목 필드로는
 *  표현되지 않고 별도 모듈이 됐다.
 *
 *  2026-09-24 실측(실DB + 실 API):
 *  | 축 | 지표 | 범위 |
 *  |---|---|---|
 *  | region_quarter | neighborhood_type · night_index · fnb_share · operating_months | 20211~20262 전 22분기 × 422행 **공백 없음** |
 *  | industry_year  | 일반 8업종 × 3지표 | 2019~2026 전 연도 |
 *  | industry_year  | childcare · convenience_store × store_count | **2026년만** |
 *  | industry_year  | childcare · convenience_store × closure_rate · growth_rate | **전 연도 없음**(원천에 개폐업 이력이 없다) |
 *  | industry_year  | academy × closure_rate · growth_rate | **전 연도 없음**(폐원일자를 주지 않는 원천 — 백엔드 v0.35.3부터 NULL) */

import type { MapMetricKey } from "@/shared/api/types";
import type { IndustryId } from "@/shared/industries";
import {
  METRICS,
  NO_CLOSURE_HISTORY_INDUSTRIES,
  SNAPSHOT_INDUSTRIES,
  YEARS,
  metricGroupOf,
  type MapState,
} from "./map-state";
import { QUARTERS } from "./quarters";

/** 스냅샷 원천이 유일하게 갖는 지표. 개폐업 이력이 없어 폐업률·성장률은 백엔드가 NULL로 둔다. */
export const SNAPSHOT_METRIC: MapMetricKey = "store_count";

/** 스냅샷 원천은 "최신 관측일의 연도"에만 적재된다(백엔드 `SnapshotStoreCount.year`).
 *  화면의 마지막 연도와 같은 값이라 상수로 박지 않고 파생한다 — 적재가 2027로 넘어가면 `YEARS`만 올리면 된다.
 *  둘이 어긋나는 짧은 창(연도 목록만 먼저 늘어난 때)에는 빈 지도가 되는데, `map-view`의 안내가 받아낸다. */
export const SNAPSHOT_YEAR = YEARS[YEARS.length - 1];

function isSnapshotIndustry(industry: string): boolean {
  return SNAPSHOT_INDUSTRIES.has(industry as IndustryId);
}

/** 이 (지표, 업종)으로 고를 수 있는 연도. 업종 축이 아닌 지표는 연도를 쓰지 않으므로 전 목록. */
export function availableYears(metric: MapMetricKey, industry: string): readonly number[] {
  if (metricGroupOf(metric).axis !== "industry_year") return YEARS;
  if (!isSnapshotIndustry(industry)) return YEARS;
  // 폐업률·성장률은 어느 연도에도 없다 — 연도를 걸러내면 원인(지표)이 가려진다.
  // 범위를 좁히는 대신 `map-view`의 "점포수를 선택해 보세요" 안내가 설명하게 둔다.
  if (metric !== SNAPSHOT_METRIC) return YEARS;
  return [SNAPSHOT_YEAR];
}

/** 이 지표로 고를 수 있는 분기. 현재 동네 지표 4종 모두 22분기가 빠짐없이 차 있다(위 실측표).
 *  지표마다 범위가 갈리면 여기서 나눈다 — 셀렉터가 이 함수만 보게 해 둔 이유다. */
export function availableQuarters(_metric: MapMetricKey): readonly string[] {
  return QUARTERS;
}

/** 범위를 벗어난 시점을 가장 가까운 유효 시점으로 당긴다. 멱등이다(유효한 값은 그대로 돌려준다). */
export function clampToCoverage(state: MapState): MapState {
  const years = availableYears(state.metric, state.industry);
  if (years.includes(state.year)) return state;
  // 가장 가까운 유효 연도 — 스냅샷은 후보가 하나뿐이고, 일반 업종은 이 분기를 타지 않는다.
  const nearest = years.reduce((best, y) =>
    Math.abs(y - state.year) < Math.abs(best - state.year) ? y : best,
  );
  return { ...state, year: nearest };
}

/** 지표 전체가 이 업종에 없는 경우 — 연도를 바꿔도 빈 지도다. `map-view` 안내가 이 사실을 말한다.
 *  스냅샷 2종뿐 아니라 학원도 폐업률·성장률이 없다(점포수는 전 연도에 있다). */
export function isMetricMissingForIndustry(metric: MapMetricKey, industry: string): boolean {
  return (
    metricGroupOf(metric).axis === "industry_year" &&
    NO_CLOSURE_HISTORY_INDUSTRIES.has(industry as IndustryId) &&
    metric !== SNAPSHOT_METRIC
  );
}

/** 모든 지표가 무리에 등록돼 있는지 — 커버리지 규칙이 빠진 지표를 조용히 통과시키지 않게 한다. */
export const COVERED_METRICS: readonly MapMetricKey[] = METRICS;
