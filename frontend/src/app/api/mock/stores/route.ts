import { INDUSTRIES, type IndustryId } from "@/shared/industries";
import { SEOUL_REGIONS_GEOJSON, storesOf } from "../fixtures";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const region = searchParams.get("region") ?? "";
  const industry = searchParams.get("industry") ?? "";

  const knownRegion = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === region);
  if (!knownRegion) {
    return Response.json(
      { error: { code: "REGION_NOT_FOUND", message: `알 수 없는 region_code: ${region}` } },
      { status: 404 },
    );
  }

  // metrics 라우트의 METRIC_NOT_FOUND 가드와 대칭 — 미지원 industry는 500이 아니라 404로 응답한다.
  if (!INDUSTRIES.includes(industry as IndustryId)) {
    return Response.json(
      { error: { code: "INDUSTRY_NOT_FOUND", message: `지원하지 않는 industry: ${industry}` } },
      { status: 404 },
    );
  }

  return Response.json(storesOf(region, industry));
}
