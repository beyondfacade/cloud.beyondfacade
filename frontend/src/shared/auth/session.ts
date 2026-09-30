import type { QueryClient } from "@tanstack/react-query";
import { LOGIN_PATH } from "@/shared/admin-gate";
import { ApiError, apiGet, apiPost } from "@/shared/api/client";
import type { AdminMe, AdminRole } from "@/shared/api/types";

/** 공용 로그인 상태 — 상단 바·랜딩·로그인 화면·관제실이 함께 본다. 세션은 httpOnly 쿠키라 JS는 토큰을 모른다. */
export const SESSION_QUERY_KEY = ["session", "me"] as const;
export const SIGNUP_PATH = "/signup";

export const GRADE_LABEL: Record<AdminRole, string> = { viewer: "일반", operator: "관리자" };

/** 비로그인(401)은 오류가 아니라 null. */
export async function fetchSession(): Promise<AdminMe | null> {
  try {
    return await apiGet<AdminMe>("/admin/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.code === "UNAUTHENTICATED") return null;
    throw error;
  }
}

export function logout(): Promise<void> {
  return apiPost<void>("/admin/auth/logout", {});
}

/** 로그인·가입·로그아웃 직후 — 헤더는 바로 바뀌고, 이전 사람의 관제실 캐시는 버린다. */
export function replaceSession(client: QueryClient, me: AdminMe | null): void {
  client.setQueryData(SESSION_QUERY_KEY, me);
  client.removeQueries({ queryKey: ["admin"] });
}

const AUTH_PAGES = [LOGIN_PATH, SIGNUP_PATH];

/** 로그인 후 돌아갈 곳 — 같은 사이트 경로만, 로그인·가입 화면 자신은 제외. */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return "/";
  const onAuthPage = AUTH_PAGES.some((page) => next === page || next.startsWith(`${page}?`) || next.startsWith(`${page}/`));
  return onAuthPage ? "/" : next;
}

export const loginHref = (next: string) => `${LOGIN_PATH}?next=${encodeURIComponent(next)}`;
export const signupHref = (next: string) => `${SIGNUP_PATH}?next=${encodeURIComponent(next)}`;
