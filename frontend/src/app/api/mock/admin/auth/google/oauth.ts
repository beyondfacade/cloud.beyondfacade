/** mock 구글 왕복 — 구글을 거치지 않고 start → callback으로 바로 넘긴다. 쿠키 이름·302 계약은 실 API와 같다. */
export const OAUTH_COOKIE = "metabole_oauth";
export const MOCK_STATE = "mock-state";

export function oauthCookie(value: string | null): string {
  return value
    ? `${OAUTH_COOKIE}=${value}; HttpOnly; Path=/; SameSite=Lax; Max-Age=600`
    : `${OAUTH_COOKIE}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0`;
}

export function readOauthCookie(request: Request): { state: string; next: string } | null {
  const cookie = request.headers.get("cookie") ?? "";
  const value = cookie.split(/;\s*/).find((c) => c.startsWith(`${OAUTH_COOKIE}=`))?.slice(OAUTH_COOKIE.length + 1);
  const [state, next] = value?.split(".", 2) ?? [];
  return state && next ? { state, next: decodeURIComponent(next) } : null;
}

export function redirect(location: string, cookies: string[]): Response {
  const headers = new Headers({ location });
  for (const cookie of cookies) headers.append("set-cookie", cookie);
  return new Response(null, { status: 302, headers });
}
