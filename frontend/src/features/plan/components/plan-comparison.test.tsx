import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FinanceInput, FinanceResult } from "@/shared/api/types";
import { emptyDraft, recordCalculation } from "../lib/plan-draft";
import { PlanComparison } from "./plan-comparison";

const input: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_500_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03, equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.048, expected_monthly_revenue: 8_000_000,
};
const result = (need: number): FinanceResult => ({
  capex: 50_000_000, monthly_fixed: 3_600_000, bep_revenue: 9_000_000, funding_gap: 6_600_000, reserve_months: 6,
  operating_reserve: 21_600_000, total_required_funds: 71_600_000, external_funding_need: need, scenarios: [], stress: [],
});

describe("계획 비교", () => {
  it("최초안이 없으면 그리지 않는다", () => {
    const { container } = render(<PlanComparison draft={emptyDraft({ region: "x", industry: "cafe" })} stale={false} onSelect={() => {}} onReasonChange={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("최초안·현재안을 나란히 놓고 조달 필요액이 갈린다", () => {
    let draft = recordCalculation(emptyDraft({ region: "x", industry: "cafe" }), input, result(31_600_000), ["key_money"]);
    draft = recordCalculation(draft, { ...input, monthly_rent: 1_000_000 }, result(22_600_000));
    render(<PlanComparison draft={draft} stale={false} onSelect={() => {}} onReasonChange={() => {}} />);
    expect(screen.getByText("3,160만 원")).toBeInTheDocument();
    expect(screen.getByText("2,260만 원")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "현재안" })).toBeChecked();
  });

  it("수정 후 미계산이면 안내가 뜨고 선택이 잠긴다", () => {
    const draft = recordCalculation(emptyDraft({ region: "x", industry: "cafe" }), input, result(31_600_000));
    render(<PlanComparison draft={draft} stale onSelect={() => {}} onReasonChange={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("아래 결과는 이전 입력 기준이에요");
    expect(screen.getByRole("radio", { name: "최초안" })).toBeDisabled();
  });

  it("미입력 0원 항목을 알려준다", () => {
    const draft = recordCalculation(emptyDraft({ region: "x", industry: "cafe" }), input, result(31_600_000), ["key_money"]);
    render(<PlanComparison draft={draft} stale={false} onSelect={() => {}} onReasonChange={() => {}} />);
    expect(screen.getByText(/권리금 — 유효한 0원인지/)).toBeInTheDocument();
  });
});
