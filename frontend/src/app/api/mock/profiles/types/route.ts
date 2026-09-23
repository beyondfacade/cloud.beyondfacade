import { LATEST_PROFILE_QUARTER, profileTypeRows } from "../../fixtures";

/** 범주 계약 — 숫자 계약(`/profiles?metric=`)과 경로를 나눈다. 정적 세그먼트 `types`가 `[regionCode]`보다 우선한다. */
export async function GET(request: Request) {
  const yearQuarter = new URL(request.url).searchParams.get("year_quarter") ?? LATEST_PROFILE_QUARTER;
  return Response.json(profileTypeRows(yearQuarter));
}
