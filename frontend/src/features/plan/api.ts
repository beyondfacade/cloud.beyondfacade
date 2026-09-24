import { apiGet, apiPost } from "@/shared/api/client";
import type {
  FinanceInput,
  FinancePrefill,
  FinanceResult,
  FundingCandidateList,
  PlanQuestion,
  PlanQuestionsRequest,
} from "@/shared/api/types";

/** 계산은 서버가 한다 — 화면은 결과를 믿고 다시 계산하지 않는다. */
export function simulateFinance(input: FinanceInput): Promise<FinanceResult> {
  return apiPost<FinanceResult>("/finance/simulate", input);
}

/** 동×업종의 실측 프리필. 값마다 출처·단서가 따라온다. 404 REGION_NOT_FOUND | INDUSTRY_NOT_FOUND. */
export function fetchFinancePrefill(regionCode: string, industryId: string): Promise<FinancePrefill> {
  const params = new URLSearchParams({ region: regionCode, industry: industryId });
  return apiGet<FinancePrefill>(`/finance/prefill?${params.toString()}`);
}

/** 후보 공고 — 지역·대상·마감으로 거른 상위 8건. 업종·금액은 필터에 쓰이지 않고 문장용으로 되돌아온다. */
export function fetchFundingCandidates(
  industryId: string | null,
  need: number | null,
  stage: string,
): Promise<FundingCandidateList> {
  const params = new URLSearchParams({ stage });
  if (industryId) params.set("industry", industryId);
  if (need != null) params.set("need", String(need));
  return apiGet<FundingCandidateList>(`/funding/candidates?${params.toString()}`);
}

/** 확인할 질문 초안. 계산 결과를 보내지 않는다 — 서버가 input으로 다시 계산한다. */
export function fetchPlanQuestions(request: PlanQuestionsRequest): Promise<PlanQuestion[]> {
  return apiPost<{ questions: PlanQuestion[] }>("/finance/questions", request).then((r) => r.questions);
}
