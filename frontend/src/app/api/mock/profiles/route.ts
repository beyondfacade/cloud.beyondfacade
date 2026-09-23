import { LATEST_PROFILE_QUARTER, profileMetricRows } from "../fixtures";
import type { ProfileMetricKey } from "@/shared/api/types";

/** 숫자 계약(`/profiles?metric=`) — 범주 계약 `/profiles/types`와 경로를 나눈다.
 *  실 API는 7종을 지원하지만 mock은 화면이 노출하는 둘만 흉내 낸다. 미지원은 500이 아니라 404. */
const SUPPORTED_METRICS: ProfileMetricKey[] = ["night_index", "fnb_share"];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const metric = (searchParams.get("metric") ?? "") as ProfileMetricKey;
  const yearQuarter = searchParams.get("year_quarter") ?? LATEST_PROFILE_QUARTER;

  if (!SUPPORTED_METRICS.includes(metric)) {
    return Response.json(
      { error: { code: "METRIC_NOT_FOUND", message: `지원하지 않는 metric: ${metric}` } },
      { status: 404 },
    );
  }

  return Response.json(profileMetricRows(metric, yearQuarter));
}
