import { LATEST_HOUR_GAP_QUARTER, SEOUL_REGIONS_GEOJSON, hourGapOf } from "../fixtures";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const region = searchParams.get("region");
  const industry = searchParams.get("industry");
  const yearQuarter = searchParams.get("year_quarter") ?? LATEST_HOUR_GAP_QUARTER;

  // 필수 파라미터 누락은 실 API(FastAPI)와 같이 422
  if (!region || !industry) {
    return Response.json({ error: { code: "VALIDATION_ERROR", message: "region·industry는 필수입니다" } }, { status: 422 });
  }
  const known = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === region);
  const gap = known && /^\d{4}[1-4]$/.test(yearQuarter) ? hourGapOf(region, industry, yearQuarter) : null;
  // 그 동에 그 업종 매출이 없는 조합 — 실 API 계약 그대로
  if (!gap) {
    return Response.json(
      { error: { code: "HOUR_GAP_NOT_FOUND", message: `시간대 어긋남 자료가 없습니다: ${region}×${industry}` } },
      { status: 404 },
    );
  }
  return Response.json(gap);
}
