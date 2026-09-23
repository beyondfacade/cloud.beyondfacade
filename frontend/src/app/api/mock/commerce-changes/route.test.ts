import { expect, it } from "vitest";
import { GET } from "./route";

function call(query: string) {
  return GET(new Request(`http://test/api/mock/commerce-changes${query}`));
}

it("지원 metric은 200과 region_code·value 쌍 목록을 반환한다", async () => {
  const res = await call("?metric=operating_months");
  expect(res.status).toBe(200);
  const rows = await res.json();
  expect(rows.length).toBeGreaterThan(400);
  expect(Object.keys(rows[0]).sort()).toEqual(["region_code", "value"]);
});

it("업종을 넘겨도 값이 달라지지 않는다 (동 단위 지표 계약)", async () => {
  const withIndustry = await (await call("?metric=operating_months&industry=cafe")).json();
  const without = await (await call("?metric=operating_months")).json();
  expect(withIndustry).toEqual(without);
});

it("분기를 생략하면 최신 분기를 쓰고, 지정하면 값이 달라진다", async () => {
  const latest = await (await call("?metric=operating_months")).json();
  const pinned = await (await call("?metric=operating_months&year_quarter=20262")).json();
  const older = await (await call("?metric=operating_months&year_quarter=20251")).json();
  expect(latest).toEqual(pinned);
  expect(older).not.toEqual(latest);
});

it("값은 실측 범위(31~206개월) 안의 정수다", async () => {
  const rows = await (await call("?metric=operating_months")).json();
  for (const row of rows) {
    expect(Number.isInteger(row.value)).toBe(true);
    expect(row.value).toBeGreaterThanOrEqual(31);
    expect(row.value).toBeLessThanOrEqual(206);
  }
});

it("미지원 metric은 500이 아니라 404 METRIC_NOT_FOUND다", async () => {
  const res = await call("?metric=closure_rate");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("METRIC_NOT_FOUND");
});
