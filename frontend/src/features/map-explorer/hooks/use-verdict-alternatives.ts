"use client";

import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/client";
import { isVerdictIndustry } from "@/shared/verdict";
import { fetchVerdictAlternatives } from "../api";

/** 대안 두 축 조회 — use-verdict와 같은 규칙(제외 업종은 요청 안 함, 404는 재시도 안 함). queryKey ["verdict-alternatives", 동, 업종]. */
export function useVerdictAlternatives(regionCode: string, industry: string) {
  return useQuery({
    queryKey: ["verdict-alternatives", regionCode, industry],
    queryFn: () => fetchVerdictAlternatives(regionCode, industry),
    enabled: isVerdictIndustry(industry),
    retry: (count, error) => !(error instanceof ApiError) && count < 1,
  });
}
