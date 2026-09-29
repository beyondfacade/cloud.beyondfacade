import { INDUSTRIES, type IndustryId } from "@/shared/industries";

/**
 * 스냅샷 원천 업종 — 개폐업 이력이 없어 폐업률·성장률이 NULL일 수 있음.
 * 사이드패널의 데이터 안내와 폐업 마커 토글에 사용한다.
 */
export const SNAPSHOT_INDUSTRIES = new Set<IndustryId>(["childcare", "convenience_store"]);

/** 개폐업 이력이 없는 업종 — 스냅샷 2종 + 학원(서울 학원 API는 폐원일자를 주지 않는다).
 *  백엔드가 폐업률·성장률을 NULL로 두는 집합. 학원은 점포수가 전 연도에 있어 스냅샷 집합과는 다르다. */
export const NO_CLOSURE_HISTORY_INDUSTRIES = new Set<IndustryId>([...SNAPSHOT_INDUSTRIES, "academy"]);

export interface MapState {
  industry: string;
  region: string | null;
  /** 관문에서 온 예산(원). 지도는 소비하지 않지만 실어두지 않으면 첫 상태 변경 때 URL에서 사라진다 — T3 프리필 원천. */
  budget: number | null;
}

export const DEFAULT_STATE: MapState = {
  industry: "cafe",
  region: null,
  budget: null,
};

export function serializeMapState(state: MapState): string {
  const params = new URLSearchParams();
  params.set("industry", state.industry);
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
  const region = sp.get("region");
  const budget = Number(sp.get("budget"));

  return {
    industry: INDUSTRIES.includes(industry as IndustryId) ? industry! : DEFAULT_STATE.industry,
    region: region || null,
    budget: Number.isInteger(budget) && budget > 0 ? budget : null,
  };
}
