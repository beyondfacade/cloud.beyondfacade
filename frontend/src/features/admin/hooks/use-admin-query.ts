"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, type QueryKey } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/client";
import { ADMIN_LOGIN_PATH } from "@/shared/admin-gate";
import { fetchAdminMe } from "../api";

export const isUnauthenticated = (error: unknown) => error instanceof ApiError && error.code === "UNAUTHENTICATED";

/** 세션 만료(401)는 어느 요청에서 나든 로그인으로 돌려보낸다 — 쿠키 게이트는 낙관적이라 실제 판정은 백엔드 몫. */
export function useUnauthenticatedRedirect(error: unknown) {
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (isUnauthenticated(error)) router.replace(`${ADMIN_LOGIN_PATH}?next=${encodeURIComponent(pathname)}`);
  }, [error, pathname, router]);
}

/** 관리자 스냅샷 폴링 — ApiError(4xx 계약 오류)는 재시도하지 않는다. 탭이 숨겨지면 폴링도 멈춘다(기본값). */
export function useAdminQuery<T>(queryKey: QueryKey, queryFn: () => Promise<T>, pollMs?: number) {
  const query = useQuery({
    queryKey,
    queryFn,
    refetchInterval: pollMs,
    staleTime: 0,
    retry: (count, error) => !(error instanceof ApiError) && count < 1,
  });
  useUnauthenticatedRedirect(query.error);
  return query;
}

export function useAdminMe() {
  return useAdminQuery(["admin", "me"], fetchAdminMe);
}
