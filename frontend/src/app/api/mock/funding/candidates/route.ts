import type { FundingCandidateList } from "@/shared/api/types";
import { fundingCandidatesOf, rankFundingByQuestion } from "../../fixtures";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stage = searchParams.get("stage");
  const industry = searchParams.get("industry");
  const needRaw = searchParams.get("need");
  const need = needRaw !== null && Number.isFinite(Number(needRaw)) ? Number(needRaw) : null;
  const q = searchParams.get("q")?.trim().slice(0, 200) ?? "";
  const candidates = fundingCandidatesOf(stage);
  const ranked = q ? rankFundingByQuestion(candidates, q) : [];
  const hasRelevant = ranked.some(({ score }) => score > 0);

  // 실 API와 같은 계약 — 셋 다 선택이고, industry·need는 필터에 쓰이지 않고 그대로 돌아간다.
  const response: FundingCandidateList = {
    candidates: hasRelevant ? ranked.map(({ item }) => item) : candidates,
    order: hasRelevant ? "relevance" : "deadline",
    industry_id: industry,
    external_funding_need: need,
    stage,
  };
  return Response.json(response);
}
