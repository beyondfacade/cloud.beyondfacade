/** 업종 id ↔ 표기 라벨. id는 URL 파라미터·API 계약 값이므로 영문을 유지하고, 화면에는 라벨만 노출한다.
 *  지도 탐색·AI 분석 두 feature가 함께 쓰는 공통 어휘이므로 shared에 둔다 (feature 간 직접 import 금지). */
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

export type IndustryId = (typeof INDUSTRIES)[number];

export const INDUSTRY_LABELS: Record<IndustryId, string> = {
  cafe: "카페",
  convenience_store: "편의점",
  hair_salon: "미용실",
  karaoke: "노래방",
  pc_bang: "PC방",
  gym: "헬스장",
  billiard: "당구장",
  real_estate: "부동산중개업",
  academy: "학원",
  childcare: "어린이집",
};

/** 알 수 없는 id는 원문을 그대로 돌려준다 (딥링크로 임의 값이 들어올 수 있음). */
export function industryLabel(id: string): string {
  return INDUSTRY_LABELS[id as IndustryId] ?? id;
}
