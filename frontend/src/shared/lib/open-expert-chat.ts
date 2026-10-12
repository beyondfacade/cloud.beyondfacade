/** 전문가와 연결하기 — 어느 화면에서든 글로벌 채팅 창을 열어 DM 전문가 목록을 보여 준다(채팅 창이 이 이벤트를 듣는다). */
export const EXPERT_CHAT_EVENT = "metabole:expert-chat";
const INDUSTRY_KEY = "metabole-expert-industry";

export function openExpertChat() {
  window.dispatchEvent(new Event(EXPERT_CHAT_EVENT));
}

/** 리포트로 분석한 업종 라벨(예: 부동산중개업) — 같은 브라우저 탭 동안 전문가 목록이 이 업종 전문가를 맨 위로 올린다. */
export function rememberExpertIndustry(label: string) {
  try {
    sessionStorage.setItem(INDUSTRY_KEY, label);
  } catch {
    // 저장소를 못 써도 목록 순서만 기본으로 남는다
  }
}

export function rememberedExpertIndustry(): string | null {
  try {
    return sessionStorage.getItem(INDUSTRY_KEY);
  } catch {
    return null;
  }
}
