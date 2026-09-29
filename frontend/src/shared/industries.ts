/** 업종 id ↔ 표기 라벨. id는 URL 파라미터·API 계약 값이므로 영문을 유지하고, 화면에는 라벨만 노출한다.
 *  지도 탐색·AI 분석 두 feature가 함께 쓰는 공통 어휘이므로 shared에 둔다 (feature 간 직접 import 금지).
 *
 *  라벨은 백엔드 마스터 `industry`에 있는 업종 전부(비노출 `restaurant_other` 제외)를 갖는다 — 딥링크·API 응답에
 *  학원·어린이집이 들어와도 이름을 그려야 하기 때문. 화면의 업종 select·관문 칩은 14종이며, 판정 대상은 `shared/verdict.ts`가 정한다(현재 12종)
 *  (HANDOFF §0-11: 학원·어린이집은 정주 인구 보조축으로 전환, 적재·API는 유지하되 선택 UI에서만 제외). */
export const INDUSTRY_LABELS = {
  cafe: "카페",
  convenience_store: "편의점",
  hair_salon: "미용실",
  real_estate: "부동산중개업",
  korean_food: "한식",
  chinese_food: "중식",
  japanese_food: "일식",
  western_food: "양식",
  snack: "분식",
  pub: "호프·주점",
  karaoke: "노래방",
  pc_bang: "PC방",
  gym: "헬스장",
  billiard: "당구장",
  academy: "학원",
  childcare: "어린이집",
} as const satisfies Record<string, string>;

export type IndustryId = keyof typeof INDUSTRY_LABELS;

/** select 업종을 `<optgroup>`으로 묶는 축. 백엔드 `industry.demand_type`(daily·leisure·macro)을 따르되
 *  음식 6종은 daily에서 떼어 첫 그룹으로 올린다 — 골목상권의 핵심이 음식이라 목록 맨 위에 둔다(설계서 §4-2).
 *  호프·주점은 demand_type이 leisure지만 사용자는 먹고 마시는 업종으로 찾으므로 음식에 둔다. */
export const INDUSTRY_GROUPS = [
  { label: "음식", ids: ["korean_food", "chinese_food", "japanese_food", "western_food", "snack", "pub"] },
  { label: "생활", ids: ["cafe", "convenience_store", "hair_salon", "real_estate"] },
  { label: "여가", ids: ["karaoke", "pc_bang", "gym", "billiard"] },
] as const satisfies readonly { label: string; ids: readonly IndustryId[] }[];

/** 업종 select 14종 — 관문 칩·예시 질문도 쓰며 순서는 그룹 순서 그대로. 판정 대상은 `shared/verdict.ts`가 정한다(현재 12종). */
export const INDUSTRIES: readonly IndustryId[] = INDUSTRY_GROUPS.flatMap((group) => group.ids);

/** 마스터에 있는 업종인가 — 판정 대상이 아니어도(학원·어린이집) API·mock은 계속 응답해야 하므로 select 목록과 구분한다. */
export function isKnownIndustry(id: string): id is IndustryId {
  return id in INDUSTRY_LABELS;
}

/** 알 수 없는 id는 원문을 그대로 돌려준다 (딥링크로 임의 값이 들어올 수 있음). */
export function industryLabel(id: string): string {
  return isKnownIndustry(id) ? INDUSTRY_LABELS[id] : id;
}
