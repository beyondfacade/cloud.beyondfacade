import { apiGet, apiPost } from "@/shared/api/client";
import type { FinanceInput, FinancePrefill, FinanceResult } from "@/shared/api/types";

/** 계산은 서버가 한다 — 화면은 결과를 믿고 다시 계산하지 않는다. */
export function simulateFinance(input: FinanceInput): Promise<FinanceResult> {
  return apiPost<FinanceResult>("/finance/simulate", input);
}

/** 동×업종의 실측 프리필. 값마다 출처·단서가 따라온다. 404 REGION_NOT_FOUND | INDUSTRY_NOT_FOUND. */
export function fetchFinancePrefill(regionCode: string, industryId: string): Promise<FinancePrefill> {
  const params = new URLSearchParams({ region: regionCode, industry: industryId });
  return apiGet<FinancePrefill>(`/finance/prefill?${params.toString()}`);
}
