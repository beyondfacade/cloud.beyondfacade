import { apiGet, apiPost } from "@/shared/api/client";
import type { AdminMe, AuthProviders, SignupRequest } from "@/shared/api/types";
import { config } from "@/shared/config";

/** loginId는 계정명 또는 이메일 — 백엔드가 @ 유무로 가른다. */
export function login(loginId: string, password: string): Promise<AdminMe> {
  return apiPost<AdminMe>("/admin/auth/login", { username: loginId, password });
}

export function signup(body: SignupRequest): Promise<AdminMe> {
  return apiPost<AdminMe>("/admin/auth/signup", body);
}

export function fetchProviders(): Promise<AuthProviders> {
  return apiGet<AuthProviders>("/admin/auth/providers");
}

/** 구글 로그인은 fetch가 아니라 페이지 이동 — 백엔드가 구글로 보내고, 돌아오면 세션 쿠키를 심어 next로 보낸다. */
export function googleStartHref(next: string): string {
  return `${config.apiBase}/admin/auth/google/start?next=${encodeURIComponent(next)}`;
}
