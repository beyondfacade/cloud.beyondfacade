import { LATEST_CHANGE_QUARTER, changeMetricRows } from "../fixtures";
import type { RegionMetricKey } from "@/shared/api/types";

const SUPPORTED_METRICS: RegionMetricKey[] = ["operating_months"];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const metric = (searchParams.get("metric") ?? "") as RegionMetricKey;
  const yearQuarter = searchParams.get("year_quarter") ?? LATEST_CHANGE_QUARTER;

  // metrics 라우트와 대칭 — 미지원 metric은 500이 아니라 404다. 업종 파라미터는 받지 않는다
  if (!SUPPORTED_METRICS.includes(metric)) {
    return Response.json(
      { error: { code: "METRIC_NOT_FOUND", message: `지원하지 않는 metric: ${metric}` } },
      { status: 404 },
    );
  }

  return Response.json(changeMetricRows(metric, yearQuarter));
}
