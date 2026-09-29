import { SEOUL_REGIONS_GEOJSON, alternativesOf, isJudgedIndustry } from "../../../fixtures";

/** 대안 두 축 — 404 규칙은 단건 라우트와 같다 (설계서 §12). */
export async function GET(request: Request, { params }: { params: Promise<{ regionCode: string }> }) {
  const { regionCode } = await params;
  const industry = new URL(request.url).searchParams.get("industry") ?? "";
  if (!isJudgedIndustry(industry)) {
    return Response.json(
      { error: { code: "INDUSTRY_NOT_FOUND", message: `판정 대상 업종이 아닙니다: ${industry}` } },
      { status: 404 },
    );
  }
  const known = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === regionCode);
  if (!known) {
    return Response.json(
      { error: { code: "VERDICT_NOT_FOUND", message: `판정이 없습니다: ${regionCode} × ${industry}` } },
      { status: 404 },
    );
  }
  return Response.json(alternativesOf(regionCode, industry));
}
