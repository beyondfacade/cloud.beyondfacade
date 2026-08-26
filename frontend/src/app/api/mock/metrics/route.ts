import { metricRows } from "../fixtures";
import { INDUSTRIES, type IndustryId } from "@/shared/industries";
import type { MetricKey } from "@/shared/api/types";

const SUPPORTED_METRICS: MetricKey[] = ["closure_rate", "growth_rate", "store_count"];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const metric = (searchParams.get("metric") ?? "closure_rate") as MetricKey;
  const year = Number(searchParams.get("year") ?? new Date().getFullYear());
  const industry = searchParams.get("industry") ?? "";

  // summary 라우트의 REGION_NOT_FOUND 가드와 대칭 — 미지원 metric은 500이 아니라 404로 응답한다.
  if (!SUPPORTED_METRICS.includes(metric)) {
    return Response.json(
      { error: { code: "METRIC_NOT_FOUND", message: `지원하지 않는 metric: ${metric}` } },
      { status: 404 },
    );
  }

  // stores 라우트의 INDUSTRY_NOT_FOUND 가드와 대칭 — 미지원 industry는 500이 아니라 404로 응답한다.
  if (!INDUSTRIES.includes(industry as IndustryId)) {
    return Response.json(
      { error: { code: "INDUSTRY_NOT_FOUND", message: `지원하지 않는 industry: ${industry}` } },
      { status: 404 },
    );
  }

  return Response.json(metricRows(metric, year, industry));
}
