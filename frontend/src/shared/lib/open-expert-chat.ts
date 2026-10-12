/** 전문가와 연결하기 — 어느 화면에서든 글로벌 채팅 창을 열어 전문가와의 1:1 방으로 보낸다(채팅 창이 이 이벤트를 듣는다). */
export const EXPERT_CHAT_EVENT = "metabole:expert-chat";

export function openExpertChat() {
  window.dispatchEvent(new Event(EXPERT_CHAT_EVENT));
}
