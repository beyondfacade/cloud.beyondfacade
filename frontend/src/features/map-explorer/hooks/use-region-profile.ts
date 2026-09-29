"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchRegionProfile } from "../api";

/** 동네 프로필 조회 — null이면 API가 해당 동의 최신 분기를 선택한다. */
export function useRegionProfile(regionCode: string, yearQuarter: string | null) {
  return useQuery({
    queryKey: ["region-profile", regionCode, yearQuarter],
    queryFn: () => fetchRegionProfile(regionCode, yearQuarter ?? undefined),
  });
}
