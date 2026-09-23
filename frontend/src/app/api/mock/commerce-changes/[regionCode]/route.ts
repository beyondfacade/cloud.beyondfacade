import { LATEST_CHANGE_QUARTER, SEOUL_REGIONS_GEOJSON, commerceChangeDetailOf } from "../../fixtures";

export async function GET(request: Request, { params }: { params: Promise<{ regionCode: string }> }) {
  const { regionCode } = await params;
  const yearQuarter = new URL(request.url).searchParams.get("year_quarter") ?? LATEST_CHANGE_QUARTER;

  const known = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === regionCode);
  // 실 API와 같은 코드 — 동이 없든 그 분기가 없든 하나로 답한다
  if (!known || !/^\d{4}[1-4]$/.test(yearQuarter)) {
    return Response.json(
      { error: { code: "COMMERCE_CHANGE_NOT_FOUND", message: `상권 변화 자료가 없습니다: ${regionCode}` } },
      { status: 404 },
    );
  }
  return Response.json(commerceChangeDetailOf(regionCode, yearQuarter));
}
