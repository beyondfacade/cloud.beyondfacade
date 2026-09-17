import { SEOUL_REGIONS_GEOJSON, convenienceStoresOf } from "../fixtures";

export async function GET(request: Request) {
  const region = new URL(request.url).searchParams.get("region") ?? "";

  const knownRegion = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === region);
  if (!knownRegion) {
    return Response.json(
      { error: { code: "REGION_NOT_FOUND", message: `알 수 없는 region_code: ${region}` } },
      { status: 404 },
    );
  }

  return Response.json(convenienceStoresOf(region));
}
