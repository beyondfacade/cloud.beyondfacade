import type { FinanceInput, FinancePrefill } from "@/shared/api/types";

/** 수수료율(카드 등) 기본 — 프리필 원천이 없어 고정값. 사용자가 고친다. */
export const DEFAULT_FEE_RATIO = 0.03;
/** 금리 조회 실패 시 폴백(연 4.5%). 화면은 프리필 basis가 없으면 "기본값"으로 표기한다. */
export const FALLBACK_LOAN_RATE = 0.045;
/** 면적 기본 33㎡(10평). 월세 = 임대료(천원/㎡/월) × 면적 × 1,000. */
export const DEFAULT_AREA_M2 = 33;

/** 미입력 판정 대상 — 금액 필드만. 비율은 벤치마크·ECOS라는 출처가 있어 제외한다. */
export const AMOUNT_FIELDS = [
  "deposit", "key_money", "interior_cost", "equipment_cost",
  "monthly_rent", "monthly_payroll", "monthly_insurance",
  "equity", "desired_loan", "expected_monthly_revenue",
] as const;

export type AmountField = (typeof AMOUNT_FIELDS)[number];

export const AMOUNT_LABELS: Record<AmountField, string> = {
  deposit: "보증금",
  key_money: "권리금",
  interior_cost: "인테리어 비용",
  equipment_cost: "설비 비용",
  monthly_rent: "월세",
  monthly_payroll: "월 인건비",
  monthly_insurance: "월 보험료",
  equity: "자기자본",
  desired_loan: "희망 대출금",
  expected_monthly_revenue: "예상 월매출",
};

export interface BuildDefaultsParams {
  /** URL `budget`(원). 관문이 실어 보낸다. */
  budget?: string | null;
  prefill?: FinancePrefill | null;
  areaM2?: number;
}

export interface FormDefaults {
  values: FinanceInput;
  /** 프리필도 URL도 채우지 못해 0으로 둔 금액 필드 — 유효한 0원과 구분해 기록한다. */
  unconfirmed: AmountField[];
}

/** 월세 = rent_per_m2(천원/㎡/월) × 면적(㎡) × 1,000. 반올림. */
export function monthlyRentFrom(rentPerM2: number, areaM2: number): number {
  return Math.round(rentPerM2 * areaM2 * 1000);
}

/** URL 예산·프리필 → 폼 초기값. 채우지 못한 금액은 0 + unconfirmed. */
export function buildDefaults(params: BuildDefaultsParams): FormDefaults {
  const budget = params.budget ? Number(params.budget) : NaN;
  const equity = Number.isFinite(budget) && budget > 0 ? Math.round(budget) : 0;
  const p = params.prefill ?? null;
  const area = params.areaM2 ?? DEFAULT_AREA_M2;

  const revenue = p?.expected_monthly_revenue.value;
  const rent = p?.rent_per_m2.value;
  const values: FinanceInput = {
    deposit: 0,
    key_money: 0,
    interior_cost: 0,
    equipment_cost: 0,
    monthly_rent: rent != null ? monthlyRentFrom(rent, area) : 0,
    monthly_payroll: 0,
    monthly_insurance: 0,
    cost_ratio: p?.cost_ratio.value ?? 0.4,
    fee_ratio: DEFAULT_FEE_RATIO,
    equity,
    desired_loan: 0,
    loan_rate: p?.loan_rate.value ?? FALLBACK_LOAN_RATE,
    expected_monthly_revenue: revenue != null ? Math.round(revenue) : 0,
  };
  const unconfirmed = AMOUNT_FIELDS.filter((field) => values[field] === 0);
  return { values, unconfirmed };
}

/** 프리필 배지 문구 — 값 옆에 붙는 출처 한 줄. 프리필이 없는 필드는 배지가 없다. */
export interface PrefillBadge {
  field: keyof FinanceInput;
  label: string;
  caveat: string;
}

export function prefillBadges(prefill: FinancePrefill | null): PrefillBadge[] {
  if (!prefill) return [];
  const badges: PrefillBadge[] = [];
  const rev = prefill.expected_monthly_revenue;
  if (rev.value != null) {
    badges.push({
      field: "expected_monthly_revenue",
      label: `실측 · ${rev.basis.year_quarter} · ${rev.basis.store_count.toLocaleString("ko-KR")}점포`,
      caveat: rev.caveat,
    });
  }
  const rent = prefill.rent_per_m2;
  if (rent.value != null) {
    const zone = rent.basis.region_path.split(">").pop() ?? rent.basis.region_path;
    badges.push({ field: "monthly_rent", label: `R-ONE ${zone} 권역 · ${rent.basis.period}`, caveat: rent.caveat });
  }
  if (prefill.cost_ratio.value != null) {
    badges.push({ field: "cost_ratio", label: "업종 평균 근사", caveat: prefill.cost_ratio.caveat });
  }
  const rate = prefill.loan_rate;
  if (rate.value != null) {
    badges.push({ field: "loan_rate", label: `${rate.basis.source ?? "ECOS"} · ${rate.basis.period}`, caveat: rate.caveat });
  }
  return badges;
}
