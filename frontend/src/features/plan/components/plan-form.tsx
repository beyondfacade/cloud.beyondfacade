"use client";

import { useEffect, useMemo, useState } from "react";
import type { FinanceInput, FinancePrefill } from "@/shared/api/types";
import { AMOUNT_FIELDS, AMOUNT_LABELS, DEFAULT_AREA_M2, monthlyRentFrom, prefillBadges, type AmountField } from "../lib/form-defaults";
import { manwonToWon, wonToManwon } from "../lib/money";
import { SourceBadge } from "./source-badge";

interface PlanFormProps {
  defaults: FinanceInput;
  prefill: FinancePrefill | null;
  submitting?: boolean;
  onSubmit: (values: FinanceInput, unconfirmed: AmountField[]) => void;
  /** 제출 전 수정 감지 — 결과가 이전 입력 기준인지 페이지가 판단한다. */
  onValuesChange?: (values: FinanceInput) => void;
}

const FIELD =
  "w-full rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] tabular-nums focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";
const LABEL = "flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]";

/** 손대지 않은 0은 빈 칸으로 보여준다 — 미입력이 유효한 0원처럼 보이면 안 된다. */
function MoneyField({ name, label, value, touched, onChange, badge }: {
  name: AmountField; label: string; value: number; touched: boolean; onChange: (won: number) => void;
  badge?: { label: string; caveat: string };
}) {
  const describedBy = badge ? `${name}-caveat` : undefined;
  return (
    <label className={LABEL}>
      <span className="flex items-center justify-between gap-2">{label}{badge && <SourceBadge id={describedBy!} label={badge.label} caveat={badge.caveat} />}</span>
      <span className="flex items-center gap-2">
        <input type="number" inputMode="numeric" name={name} aria-describedby={describedBy}
          value={touched || value !== 0 ? wonToManwon(value) : ""} placeholder="미입력"
          onChange={(e) => onChange(manwonToWon(Number(e.target.value) || 0))} className={FIELD} />
        <span className="shrink-0 text-xs">만원</span>
      </span>
    </label>
  );
}

function RatioField({ name, label, value, onChange, badge }: {
  name: keyof FinanceInput; label: string; value: number; onChange: (ratio: number) => void; badge?: { label: string; caveat: string };
}) {
  const describedBy = badge ? `${name}-caveat` : undefined;
  return (
    <label className={LABEL}>
      <span className="flex items-center justify-between gap-2">{label}{badge && <SourceBadge id={describedBy!} label={badge.label} caveat={badge.caveat} />}</span>
      <span className="flex items-center gap-2">
        <input type="number" step="0.01" inputMode="decimal" name={name} aria-describedby={describedBy}
          value={Math.round(value * 10000) / 100} onChange={(e) => onChange((Number(e.target.value) || 0) / 100)} className={FIELD} />
        <span className="shrink-0 text-xs">%</span>
      </span>
    </label>
  );
}

/** 13필드 + 면적. 프리필된 값엔 출처 배지, 빈 필수값만 사용자가 채운다. */
export function PlanForm({ defaults, prefill, submitting, onSubmit, onValuesChange }: PlanFormProps) {
  const [values, setValues] = useState<FinanceInput>(defaults);
  const [touched, setTouched] = useState<Set<keyof FinanceInput>>(() => new Set());
  const [areaM2, setAreaM2] = useState(DEFAULT_AREA_M2);
  const badges = useMemo(() => new Map(prefillBadges(prefill).map((b) => [b.field, b])), [prefill]);
  const rentPerM2 = prefill?.rent_per_m2.value ?? null;

  // 프리필이 늦게 와도 사용자가 손대지 않은 칸만 따라간다.
  useEffect(() => {
    setValues((prev) => {
      const next = { ...prev };
      for (const key of Object.keys(defaults) as (keyof FinanceInput)[]) if (!touched.has(key)) next[key] = defaults[key];
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- defaults만 추적: touched는 사용자 입력 시 함께 바뀐다
  }, [defaults]);

  useEffect(() => { onValuesChange?.(values); }, [values, onValuesChange]);

  const set = (key: keyof FinanceInput) => (v: number) => {
    setTouched((t) => new Set(t).add(key));
    setValues((prev) => ({ ...prev, [key]: v }));
  };

  // 면적을 바꾸면 월세 프리필을 다시 계산한다 — 사용자가 월세를 직접 고쳤으면 건드리지 않는다.
  const changeArea = (m2: number) => {
    setAreaM2(m2);
    if (rentPerM2 != null && !touched.has("monthly_rent")) setValues((prev) => ({ ...prev, monthly_rent: monthlyRentFrom(rentPerM2, m2) }));
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const unconfirmed = AMOUNT_FIELDS.filter((f) => values[f] === 0 && !touched.has(f));
    onSubmit(values, unconfirmed);
  };

  const money = (name: AmountField) => (
    <MoneyField key={name} name={name} label={AMOUNT_LABELS[name]} value={values[name]} touched={touched.has(name)} onChange={set(name)} badge={badges.get(name)} />
  );

  return (
    <form onSubmit={submit} className="flex flex-col gap-6" aria-label="자금 계획 입력">
      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">확인해 주세요 — 채워진 값의 출처를 보고 고치세요</legend>
        {money("equity")}
        {money("expected_monthly_revenue")}
        <label className={LABEL}>면적
          <span className="flex items-center gap-2">
            <input type="number" inputMode="numeric" name="area_m2" value={areaM2} min={1} onChange={(e) => changeArea(Math.max(1, Number(e.target.value) || 1))} className={FIELD} />
            <span className="shrink-0 text-xs">㎡ {rentPerM2 != null && `(월세 = ${rentPerM2}천원/㎡ × 면적)`}</span>
          </span>
        </label>
        {money("monthly_rent")}
        <div className="grid grid-cols-3 gap-3">
          <RatioField name="cost_ratio" label="원가율" value={values.cost_ratio} onChange={set("cost_ratio")} badge={badges.get("cost_ratio")} />
          <RatioField name="fee_ratio" label="수수료율" value={values.fee_ratio} onChange={set("fee_ratio")} />
          <RatioField name="loan_rate" label="대출금리" value={values.loan_rate} onChange={set("loan_rate")} badge={badges.get("loan_rate")} />
        </div>
      </fieldset>
      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 text-sm font-semibold text-[var(--text-primary)]">입력해 주세요</legend>
        {money("deposit")}{money("key_money")}{money("interior_cost")}{money("equipment_cost")}
        {money("monthly_payroll")}{money("monthly_insurance")}{money("desired_loan")}
      </fieldset>
      <button type="submit" disabled={submitting}
        className="rounded-lg bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-[var(--accent-fg)] hover:opacity-90 disabled:opacity-50">
        {submitting ? "계산 중…" : "계산하기"}
      </button>
    </form>
  );
}
