import { SEOUL_REGIONS_GEOJSON, summaryOf } from "../../../fixtures";

export async function GET(request: Request, { params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const { searchParams } = new URL(request.url);
  const industry = searchParams.get("industry") ?? "";

  const known = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === code);
  if (!known) {
    return Response.json(
      { error: { code: "REGION_NOT_FOUND", message: `알 수 없는 region_code: ${code}` } },
      { status: 404 },
    );
  }

  return Response.json(summaryOf(code, industry));
}
