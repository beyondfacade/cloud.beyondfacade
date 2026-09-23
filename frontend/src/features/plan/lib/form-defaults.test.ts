import { describe, expect, it } from "vitest";
import type { FinancePrefill } from "@/shared/api/types";
import { buildDefaults, monthlyRentFrom, prefillBadges } from "./form-defaults";

function prefill(overrides: Partial<FinancePrefill> = {}): FinancePrefill {
  return {
    region_code: "1168064000",
    industry_id: "cafe",
    expected_monthly_revenue: {
      value: 26129731,
      basis: { year_quarter: "20254", quarterly_sales: 47268682633, store_count: 603, source_codes: ["CS100006", "CS100008", "CS100010"] },
      caveat: "평균입니다.",
      unit: "원/월",
    },
    rent_per_m2: {
      value: 65.51,
      basis: { region_path: "서울>강남", building_type: "medium_large", period: "2026Q2", level: "권역", small_per_m2: 64.56, source: "R-ONE" },
      caveat: "권역 평균입니다.",
      unit: "천원/㎡/월",
    },
    cost_ratio: { value: 0.35, basis: { kind: "industry_benchmark", industry_id: "cafe" }, caveat: "근사값입니다.", unit: null },
    loan_rate: { value: 0.0405, basis: { rate_type: "loan_facility", period: "202607", rate_pct: 4.05, source: "ECOS" }, caveat: "공시 평균입니다.", unit: "비율" },
    equity: null,
    ...overrides,
  };
}

describe("폼 초기값", () => {
  it("URL 예산이 자기자본이 되고 프리필 값이 들어간다", () => {
    const { values, unconfirmed } = buildDefaults({ budget: "50000000", prefill: prefill() });
    expect(values.equity).toBe(50_000_000);
    expect(values.expected_monthly_revenue).toBe(26_129_731);
    expect(values.cost_ratio).toBe(0.35);
    expect(values.loan_rate).toBe(0.0405);
    expect(unconfirmed).not.toContain("equity");
    expect(unconfirmed).not.toContain("expected_monthly_revenue");
  });

  it("월세는 임대료 × 면적(기본 33㎡) × 1,000을 반올림한 값이다", () => {
    expect(monthlyRentFrom(65.51, 33)).toBe(2_161_830);
    const { values } = buildDefaults({ prefill: prefill() });
    expect(values.monthly_rent).toBe(2_161_830);
    expect(buildDefaults({ prefill: prefill(), areaM2: 50 }).values.monthly_rent).toBe(3_275_500);
  });

  it("프리필이 null인 금액은 0으로 두고 unconfirmed에 기록한다", () => {
    const nullRevenue = prefill({
      expected_monthly_revenue: { value: null, basis: { year_quarter: "", quarterly_sales: 0, store_count: 0, source_codes: [] }, caveat: "", unit: null },
    });
    const { values, unconfirmed } = buildDefaults({ prefill: nullRevenue });
    expect(values.expected_monthly_revenue).toBe(0);
    expect(unconfirmed).toContain("expected_monthly_revenue");
    expect(unconfirmed).toContain("equity"); // 예산 없음
    expect(unconfirmed).toContain("deposit");
  });

  it("예산이 숫자가 아니거나 0 이하면 자기자본 0", () => {
    expect(buildDefaults({ budget: "abc" }).values.equity).toBe(0);
    expect(buildDefaults({ budget: "-5" }).values.equity).toBe(0);
  });

  it("배지는 프리필된 필드에만, 출처를 한 줄로", () => {
    const badges = prefillBadges(prefill());
    expect(badges.map((b) => [b.field, b.label])).toEqual([
      ["expected_monthly_revenue", "실측 · 20254 · 603점포"],
      ["monthly_rent", "R-ONE 강남 권역 · 2026Q2"],
      ["cost_ratio", "업종 평균 근사"],
      ["loan_rate", "ECOS · 202607"],
    ]);
    expect(prefillBadges(null)).toEqual([]);
  });
});
