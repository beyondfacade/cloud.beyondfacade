import { apiGet } from "@/shared/api/client";
import type { RegionSummary, SupportGuide } from "@/shared/api/types";

/** 창업 지원 정보 — 대출·보증 / 우리 구 전용 / 창업·경영 + 금리 참고값. 둘 다 선택이고, 동이 없으면 구 묶음이 빈다. */
export function fetchSupportGuide(regionCode: string | null, industryId: string | null): Promise<SupportGuide> {
  const params = new URLSearchParams();
  if (regionCode) params.set("region", regionCode);
  if (industryId) params.set("industry", industryId);
  return apiGet<SupportGuide>(`/funding/support?${params.toString()}`);
}

/** 제목 옆에 코드 대신 쓸 동네 이름. 실패해도 지원 정보는 그대로 보여 준다. */
export function fetchSupportRegion(regionCode: string, industryId: string): Promise<RegionSummary> {
  const params = new URLSearchParams({ industry: industryId });
  return apiGet<RegionSummary>(`/regions/${regionCode}/summary?${params.toString()}`);
}
