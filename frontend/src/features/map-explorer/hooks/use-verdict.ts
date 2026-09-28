"use client";

import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/client";
import { isVerdictIndustry } from "@/shared/verdict";
import { fetchVerdict } from "../api";

/** 판정 카드 조회 — 404(판정 없음·대상 아님)는 재시도하지 않는다. queryKey는 ["verdict", 동, 업종]. */
export function useVerdict(regionCode: string, industry: string) {
  return useQuery({
    queryKey: ["verdict", regionCode, industry],
    queryFn: () => fetchVerdict(regionCode, industry),
    // 편의점처럼 판정 대상이 아닌 업종은 요청하지 않는다(백엔드 404) — 카드는 isPending이 아니라 idle이 되어 그리지 않는다
    enabled: isVerdictIndustry(industry),
    retry: (count, error) => !(error instanceof ApiError) && count < 1,
  });
}
