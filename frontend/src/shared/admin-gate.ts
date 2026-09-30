/** 관리자 화면 낙관적 게이트 — 쿠키 유무만 본다. 세션 유효성·등급은 백엔드가 매 요청 검증한다. */
export const ADMIN_SESSION_COOKIE = "metabole_admin";
export const LOGIN_PATH = "/login";

export function adminGateRedirect(pathname: string, search: string, hasSession: boolean): string | null {
  if (hasSession) return null;
  return `${LOGIN_PATH}?next=${encodeURIComponent(pathname + search)}`;
}
