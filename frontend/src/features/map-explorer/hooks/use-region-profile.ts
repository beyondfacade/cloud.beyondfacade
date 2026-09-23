"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchRegionProfile } from "../api";

/** 동네 프로필 조회 — 유형 섹션과 하루 흐름 섹션이 같은 키를 쓰므로 요청은 한 번이다(TanStack Query 중복 제거). */
export function useRegionProfile(regionCode: string) {
  return useQuery({
    queryKey: ["region-profile", regionCode],
    queryFn: () => fetchRegionProfile(regionCode),
  });
}
