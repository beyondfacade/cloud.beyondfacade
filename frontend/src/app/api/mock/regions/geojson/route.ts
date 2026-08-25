import { SEOUL_SAMPLE_GEOJSON } from "../../fixtures";

export async function GET() {
  return Response.json(SEOUL_SAMPLE_GEOJSON);
}
