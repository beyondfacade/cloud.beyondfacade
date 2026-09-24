import { fundingCandidatesOf } from "../../fixtures";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stage = searchParams.get("stage");
  const industry = searchParams.get("industry");
  const needRaw = searchParams.get("need");
  const need = needRaw !== null && Number.isFinite(Number(needRaw)) ? Number(needRaw) : null;

  // 실 API와 같은 계약 — 셋 다 선택이고, industry·need는 필터에 쓰이지 않고 그대로 돌아간다.
  return Response.json({
    candidates: fundingCandidatesOf(stage),
    industry_id: industry,
    external_funding_need: need,
    stage,
  });
}
