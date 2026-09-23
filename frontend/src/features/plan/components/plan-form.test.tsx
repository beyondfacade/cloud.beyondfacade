import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { FinancePrefill } from "@/shared/api/types";
import { buildDefaults } from "../lib/form-defaults";
import { PlanForm } from "./plan-form";

const prefill: FinancePrefill = {
  region_code: "1168064000", industry_id: "cafe",
  expected_monthly_revenue: { value: 26129731, basis: { year_quarter: "20254", quarterly_sales: 1, store_count: 603, source_codes: [] }, caveat: "평균입니다.", unit: "원/월" },
  rent_per_m2: { value: 65.51, basis: { region_path: "서울>강남", building_type: "medium_large", period: "2026Q2", level: "권역" }, caveat: "권역 평균입니다.", unit: "천원/㎡/월" },
  cost_ratio: { value: 0.35, basis: { kind: "industry_benchmark" }, caveat: "근사값입니다.", unit: null },
  loan_rate: { value: 0.0405, basis: { rate_type: "loan_facility", period: "202607", source: "ECOS" }, caveat: "공시 평균입니다.", unit: "비율" },
  equity: null,
};

describe("계획 입력 폼", () => {
  it("프리필된 필드에 출처 배지가 붙고 값이 채워진다", () => {
    const { values } = buildDefaults({ budget: "50000000", prefill });
    render(<PlanForm defaults={values} prefill={prefill} onSubmit={() => {}} />);
    expect(screen.getByText("실측 · 20254 · 603점포")).toBeInTheDocument();
    expect(screen.getByText("R-ONE 강남 권역 · 2026Q2")).toBeInTheDocument();
    expect(screen.getByText("ECOS · 202607")).toBeInTheDocument();
    expect(screen.getByLabelText(/예상 월매출/)).toHaveValue(2613); // 만원
    expect(screen.getByLabelText(/^자기자본/)).toHaveValue(5000);
  });

  it("손대지 않은 0은 빈 칸이고 제출 시 unconfirmed로 넘어간다", () => {
    const onSubmit = vi.fn();
    const { values } = buildDefaults({ prefill });
    render(<PlanForm defaults={values} prefill={prefill} onSubmit={onSubmit} />);
    expect(screen.getByLabelText(/보증금/)).toHaveValue(null);
    fireEvent.click(screen.getByRole("button", { name: "계산하기" }));
    const [, unconfirmed] = onSubmit.mock.calls[0];
    expect(unconfirmed).toContain("deposit");
    expect(unconfirmed).toContain("equity");
    expect(unconfirmed).not.toContain("expected_monthly_revenue");
  });

  it("면적을 바꾸면 월세가 다시 계산된다", () => {
    const { values } = buildDefaults({ prefill });
    render(<PlanForm defaults={values} prefill={prefill} onSubmit={() => {}} />);
    fireEvent.change(screen.getByLabelText(/면적/), { target: { value: "50" } });
    expect(screen.getByLabelText(/^월세/)).toHaveValue(328); // 3,275,500원 → 328만원
  });
});
