import { isJudgedIndustry, verdictRows } from "../fixtures";

/** 위험도 단계구분도 — 범주 계약이지만 필드명은 value(실 API 미러). 판정 대상 12종 외는 404. */
export async function GET(request: Request) {
  const industry = new URL(request.url).searchParams.get("industry") ?? "";
  if (!isJudgedIndustry(industry)) {
    return Response.json(
      { error: { code: "INDUSTRY_NOT_FOUND", message: `판정 대상 업종이 아닙니다: ${industry}` } },
      { status: 404 },
    );
  }
  return Response.json(verdictRows(industry));
}
