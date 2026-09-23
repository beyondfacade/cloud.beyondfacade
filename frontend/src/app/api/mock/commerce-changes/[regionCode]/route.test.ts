import { expect, it } from "vitest";
import { GET } from "./route";
import { GET as listMetrics } from "../route";

const KNOWN = "1168064000";
function call(regionCode: string, query = "") {
  return GET(new Request(`http://test/api/mock/commerce-changes/${regionCode}${query}`), {
    params: Promise.resolve({ regionCode }),
  });
}

it("등록된 동은 200과 서울 평균이 동봉된 상세를 준다", async () => {
  const res = await call(KNOWN);
  expect(res.status).toBe(200);
  const d = await res.json();
  expect(d.region_code).toBe(KNOWN);
  expect(d.year_quarter).toBe("20262");
  expect(["LL", "HH", "LH", "HL"]).toContain(d.change_code);
  expect(d.seoul).toEqual({ operating_months: 118, closed_months: 54 });
  expect(d.closed_months).toBeLessThan(d.operating_months);
});

it("상세의 영업 개월이 단계구분도 값과 같다 — 지도 색과 패널 숫자가 어긋나지 않는다", async () => {
  const detail = await (await call(KNOWN, "?year_quarter=20262")).json();
  const rows: { region_code: string; value: number }[] = await (
    await listMetrics(new Request("http://test/api/mock/commerce-changes?metric=operating_months&year_quarter=20262"))
  ).json();
  expect(rows.find((r) => r.region_code === KNOWN)?.value).toBe(detail.operating_months);
});

it("알 수 없는 동·틀린 분기는 500이 아니라 404 COMMERCE_CHANGE_NOT_FOUND", async () => {
  expect((await call("9999999999")).status).toBe(404);
  const res = await call(KNOWN, "?year_quarter=2026");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("COMMERCE_CHANGE_NOT_FOUND");
});
