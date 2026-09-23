import { expect, it } from "vitest";
import { POST } from "./route";

const demo = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_500_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03, equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.048, expected_monthly_revenue: 8_000_000,
};
const call = (body: unknown) => POST(new Request("http://test/api/mock/finance/simulate", { method: "POST", body: JSON.stringify(body) }));

it("시연 사례를 실 API와 같은 수로 돌려준다", async () => {
  const res = await call(demo);
  expect(res.status).toBe(200);
  const r = await res.json();
  expect(r.external_funding_need).toBe(31_600_000);
  expect(r.funding_gap).toBe(6_600_000);
  expect(r.bep_revenue).toBe(9_000_000);
  expect(r.scenarios).toHaveLength(3);
  expect(r.stress).toHaveLength(2);
});

it("변동비율이 1 이상이면 실 API처럼 422", async () => {
  expect((await call({ ...demo, cost_ratio: 0.98 })).status).toBe(422);
  expect((await call({ ...demo, deposit: -1 })).status).toBe(422);
});
