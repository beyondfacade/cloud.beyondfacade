import { SEOUL_REGIONS_GEOJSON } from "../../fixtures";

export async function GET() {
  return Response.json(SEOUL_REGIONS_GEOJSON);
}
