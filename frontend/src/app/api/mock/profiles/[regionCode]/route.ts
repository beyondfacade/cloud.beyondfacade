import { LATEST_PROFILE_QUARTER, SEOUL_REGIONS_GEOJSON, regionProfileOf } from "../../fixtures";

export async function GET(request: Request, { params }: { params: Promise<{ regionCode: string }> }) {
  const { regionCode } = await params;
  const yearQuarter = new URL(request.url).searchParams.get("year_quarter") ?? LATEST_PROFILE_QUARTER;

  const known = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === regionCode);
  // 실 API와 같은 코드 — 동이 없든 그 분기가 없든 "프로필이 없다" 하나로 답한다
  if (!known || !/^\d{4}[1-4]$/.test(yearQuarter)) {
    return Response.json(
      {
        error: {
          code: "REGION_PROFILE_NOT_FOUND",
          message: `동네 프로필이 없습니다: ${regionCode}`,
        },
      },
      { status: 404 },
    );
  }

  return Response.json(regionProfileOf(regionCode, yearQuarter));
}
