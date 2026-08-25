import { metricRows } from "../fixtures";
import type { MetricKey } from "@/shared/api/types";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const metric = (searchParams.get("metric") ?? "closure_rate") as MetricKey;
  const year = Number(searchParams.get("year") ?? new Date().getFullYear());

  return Response.json(metricRows(metric, year));
}
