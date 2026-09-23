import { describe, expect, it } from "vitest";
import type { FinanceInput } from "@/shared/api/types";
import { simulate } from "./finance-engine";

/** 대구 시연 대본 사례 — 파이썬 엔진(`tests/test_finance_engine.py`)과 같은 수여야 한다. 만원→원. */
const demo: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_500_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03, equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.048,
  expected_monthly_revenue: 8_000_000,
};

describe("mock 엔진 = 파이썬 엔진", () => {
  it("월세 250만: BEP 900만 · 총 준비자금 7,160만 · 조달 필요 3,160만 · 부족 660만", () => {
    const r = simulate(demo);
    expect(r.capex).toBe(50_000_000);
    expect(r.monthly_fixed).toBe(3_600_000);
    expect(r.bep_revenue).toBe(9_000_000);
    expect(r.total_required_funds).toBe(71_600_000);
    expect(r.external_funding_need).toBe(31_600_000);
    expect(r.funding_gap).toBe(6_600_000);
    // 실 API 응답과 같은 시나리오 수치
    expect(r.scenarios.map((s) => [s.name, s.operating_profit, s.payback_months, s.runway_months])).toEqual([
      ["비관", -1_680_000, null, 8.9],
      ["기준", -400_000, null, 37.5],
      ["낙관", 1_520_000, 32.9, null],
    ]);
    expect(r.stress[0]).toEqual({ rate_delta: 0.01, monthly_fixed: 3_620_833, base_operating_profit: -420_833 });
  });

  it("월세 100만: BEP 525만 · 부족 0 · 조달 필요 2,260만", () => {
    const r = simulate({ ...demo, monthly_rent: 1_000_000 });
    expect(r.bep_revenue).toBe(5_250_000);
    expect(r.funding_gap).toBe(0);
    expect(r.external_funding_need).toBe(22_600_000);
  });
});
