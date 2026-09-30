/** 관리자 화면 낙관적 게이트 — 쿠키 유무만 본다. 세션 유효성·역할은 백엔드가 매 요청 검증한다. */
export const ADMIN_SESSION_COOKIE = "metabole_admin";
export const ADMIN_LOGIN_PATH = "/admin/login";

export function adminGateRedirect(pathname: string, search: string, hasSession: boolean): string | null {
  if (hasSession || pathname === ADMIN_LOGIN_PATH) return null;
  return `${ADMIN_LOGIN_PATH}?next=${encodeURIComponent(pathname + search)}`;
}
