import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FinanceResult } from "@/shared/api/types";
import { ResultFigures } from "./result-figures";

const result: FinanceResult = {
  capex: 50_000_000, monthly_fixed: 3_600_000, bep_revenue: 9_000_000, funding_gap: 0,
  reserve_months: 6, operating_reserve: 21_600_000, total_required_funds: 71_600_000, external_funding_need: 31_600_000,
  scenarios: [{ name: "비관", monthly_revenue: 4_800_000, variable_cost: 2_880_000, operating_profit: -1_680_000, payback_months: null, runway_months: 8.9 }],
  stress: [{ rate_delta: 0.01, monthly_fixed: 3_620_833, base_operating_profit: -420_833 }],
};

describe("계산 결과", () => {
  it("헤드라인은 자기자본 외 조달 필요다", () => {
    render(<ResultFigures result={result} />);
    expect(screen.getByText("자기자본 외 조달 필요")).toBeInTheDocument();
    expect(document.querySelector("[data-headline]")?.textContent).toBe("3,160만 원");
  });

  it("부족액이 0원이어도 '충분' 류 문구가 없다", () => {
    const { container } = render(<ResultFigures result={result} />);
    expect(container.textContent).not.toMatch(/충분|승인됐|신청 완료/);
    expect(screen.getByText(/아직 확보된 돈이 아닙니다/)).toBeInTheDocument();
  });

  it("영업이익이 음수면 회수 불가·버티는 기간을 보인다", () => {
    render(<ResultFigures result={result} />);
    expect(screen.getByText("회수 불가")).toBeInTheDocument();
    expect(screen.getByText("8.9개월")).toBeInTheDocument();
  });
});
