import { apiGet } from "@/shared/api/client";
import type { RegionSummary } from "@/shared/api/types";

/** 리포트 헤더의 동 이름 — 조회 완료 전에도 분석은 바로 시작한다. */
export function fetchAnalysisRegionSummary(region: string, industry: string): Promise<RegionSummary> {
  const params = new URLSearchParams({ industry });
  return apiGet<RegionSummary>(`/regions/${region}/summary?${params.toString()}`);
}
