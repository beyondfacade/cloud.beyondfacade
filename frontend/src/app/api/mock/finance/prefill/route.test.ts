import { expect, it } from "vitest";
import { GET } from "./route";

const call = (q: string) => GET(new Request(`http://test/api/mock/finance/prefill${q}`));

it("등록된 동×업종은 200과 값·출처·단서 네 묶음을 준다", async () => {
  const res = await call("?region=1168064000&industry=cafe");
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.expected_monthly_revenue.value).toBeGreaterThan(0);
  expect(body.expected_monthly_revenue.basis.store_count).toBeGreaterThan(0);
  expect(body.rent_per_m2.basis.region_path).toBe("서울>강남");
  expect(body.loan_rate.basis.period).toBe("202607");
  expect(body.equity).toBeNull();
});

it("같은 입력은 같은 값 (Math.random 금지)", async () => {
  const a = await (await call("?region=1168064000&industry=cafe")).json();
  const b = await (await call("?region=1168064000&industry=cafe")).json();
  expect(a).toEqual(b);
});

it("매출 원천이 없는 업종은 404가 아니라 null", async () => {
  const body = await (await call("?region=1168064000&industry=childcare")).json();
  expect(body.expected_monthly_revenue.value).toBeNull();
});

it("없는 동·업종은 404", async () => {
  expect((await call("?region=9999999999&industry=cafe")).status).toBe(404);
  expect((await (await call("?region=1168064000&industry=nope")).json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});
