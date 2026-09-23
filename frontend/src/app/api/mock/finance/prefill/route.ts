import { SEOUL_REGIONS_GEOJSON, financePrefillOf } from "../../fixtures";
import { INDUSTRIES, type IndustryId } from "@/shared/industries";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const region = searchParams.get("region") ?? "";
  const industry = searchParams.get("industry") ?? "";

  // 실 API와 같은 코드 — 없는 동·미등록 업종은 500이 아니라 404
  if (!SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === region)) {
    return Response.json({ error: { code: "REGION_NOT_FOUND", message: `알 수 없는 region_code: ${region}` } }, { status: 404 });
  }
  if (!INDUSTRIES.includes(industry as IndustryId)) {
    return Response.json({ error: { code: "INDUSTRY_NOT_FOUND", message: `지원하지 않는 industry: ${industry}` } }, { status: 404 });
  }
  return Response.json(financePrefillOf(region, industry));
}
