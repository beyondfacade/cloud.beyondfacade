import type { FinanceInput, FinanceResult, FinanceScenario, StressResult } from "@/shared/api/types";

/** 재무 엔진 TS 이식 — **mock 라우트 전용.** 화면은 서버(`POST /finance/simulate`) 결과만 믿는다.
 *  원본: `backend/apps/finance/domain/services/engine.py`(대구 `engine.py`). 산식을 바꾸지 않는다 —
 *  mock이 실 API와 같은 수를 내야 화면 개발 중 계약이 흔들리지 않는다. 파이썬 `int()`는 0 방향 절삭이라
 *  `Math.trunc`로 옮겼다. `round(x, 1)`은 은행가 반올림이라 정확히 .x5에서 갈릴 수 있다(시연 사례엔 없다). */

const SCENARIO_MULTIPLIERS: [string, number][] = [["비관", 0.6], ["기준", 1.0], ["낙관", 1.6]];
const WORKING_CAPITAL_MONTHS = 6;
const STRESS_DELTAS = [0.01, 0.02];

const round1 = (x: number) => Math.round(x * 10) / 10;

function monthlyInterest(principal: number, rate: number): number {
  return Math.trunc((principal * rate) / 12);
}

function fixed(inp: FinanceInput, rate: number): number {
  return inp.monthly_rent + monthlyInterest(inp.desired_loan, rate) + inp.monthly_insurance + inp.monthly_payroll;
}

function profitAt(revenue: number, varRatio: number, fixedCost: number): number {
  return revenue - Math.trunc(revenue * varRatio) - fixedCost;
}

export function simulate(inp: FinanceInput): FinanceResult {
  const capex = inp.deposit + inp.key_money + inp.interior_cost + inp.equipment_cost;
  const fixedCost = fixed(inp, inp.loan_rate);
  const varRatio = inp.cost_ratio + inp.fee_ratio;
  const bepRevenue = Math.trunc(fixedCost / (1 - varRatio));
  const availableCash = inp.equity + inp.desired_loan - capex;
  const operatingReserve = fixedCost * WORKING_CAPITAL_MONTHS;
  const totalRequiredFunds = capex + operatingReserve;
  const externalFundingNeed = Math.max(0, totalRequiredFunds - inp.equity);
  const fundingGap = Math.max(0, totalRequiredFunds - inp.equity - inp.desired_loan);

  const scenarios: FinanceScenario[] = SCENARIO_MULTIPLIERS.map(([name, mult]) => {
    const revenue = Math.trunc(inp.expected_monthly_revenue * mult);
    const variable = Math.trunc(revenue * varRatio);
    const profit = profitAt(revenue, varRatio, fixedCost);
    const payback = profit > 0 ? round1(capex / profit) : null;
    const runway = profit < 0 && availableCash > 0 ? round1(availableCash / -profit) : null;
    return { name, monthly_revenue: revenue, variable_cost: variable, operating_profit: profit, payback_months: payback, runway_months: runway };
  });

  const stress: StressResult[] = STRESS_DELTAS.map((d) => {
    const f = fixed(inp, inp.loan_rate + d);
    return { rate_delta: d, monthly_fixed: f, base_operating_profit: profitAt(inp.expected_monthly_revenue, varRatio, f) };
  });

  return {
    capex, monthly_fixed: fixedCost, bep_revenue: bepRevenue, funding_gap: fundingGap,
    reserve_months: WORKING_CAPITAL_MONTHS, operating_reserve: operatingReserve,
    total_required_funds: totalRequiredFunds, external_funding_need: externalFundingNeed,
    scenarios, stress,
  };
}
