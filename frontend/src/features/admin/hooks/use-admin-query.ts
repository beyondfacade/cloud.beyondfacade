"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { keepPreviousData, useInfiniteQuery, useQuery, type QueryKey } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/client";
import { LOGIN_PATH } from "@/shared/admin-gate";
import { fetchAdminMe } from "../api";

export const isUnauthenticated = (error: unknown) => error instanceof ApiError && error.code === "UNAUTHENTICATED";

/** 세션 만료(401)는 어느 요청에서 나든 로그인으로 돌려보낸다 — 쿠키 게이트는 낙관적이라 실제 판정은 백엔드 몫. */
export function useUnauthenticatedRedirect(error: unknown) {
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (isUnauthenticated(error)) router.replace(`${LOGIN_PATH}?next=${encodeURIComponent(pathname)}`);
  }, [error, pathname, router]);
}

/** 관리자 스냅샷 폴링 — ApiError(4xx 계약 오류)는 재시도하지 않는다. 탭이 숨겨지면 폴링도 멈춘다(기본값). */
export function useAdminQuery<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  pollMs?: number,
  { keepPrevious = false }: { keepPrevious?: boolean } = {},
) {
  const query = useQuery({
    queryKey,
    queryFn,
    refetchInterval: pollMs,
    placeholderData: keepPrevious ? keepPreviousData : undefined,
    staleTime: 0,
    retry: (count, error) => !(error instanceof ApiError) && count < 1,
  });
  useUnauthenticatedRedirect(query.error);
  return query;
}

/** id 커서 목록 — 다음 쪽 커서는 서버가 준 next_before_id. 폴링하지 않는다(더 보기로 쌓은 쪽이 흔들리지 않게). */
export function useAdminPages<T>(
  queryKey: QueryKey,
  fetchPage: (beforeId: number | null) => Promise<{ items: T[]; next_before_id: number | null }>,
) {
  const query = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => fetchPage(pageParam),
    initialPageParam: null as number | null,
    getNextPageParam: (last) => last.next_before_id,
    staleTime: 0,
    retry: (count, error) => !(error instanceof ApiError) && count < 1,
  });
  useUnauthenticatedRedirect(query.error);
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  return { ...query, items };
}

export function useAdminMe() {
  return useAdminQuery(["admin", "me"], fetchAdminMe);
}
