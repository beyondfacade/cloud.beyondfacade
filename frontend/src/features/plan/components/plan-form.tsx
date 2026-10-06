"use client";

import { useEffect, useMemo, useState } from "react";
import type { FinanceInput, FinancePrefill } from "@/shared/api/types";
import { AMOUNT_FIELDS, AMOUNT_LABELS, DEFAULT_AREA_M2, monthlyRentFrom, prefillBadges, type AmountField } from "../lib/form-defaults";
import { manwonToWon, wonToManwon } from "../lib/money";
import { SourceBadge } from "./source-badge";
import styles from "./plan-workspace.module.css";

interface PlanFormProps {
  defaults: FinanceInput;
  prefill: FinancePrefill | null;
  submitting?: boolean;
  onSubmit: (values: FinanceInput, unconfirmed: AmountField[]) => void;
  /** 제출 전 수정 감지 — 결과가 이전 입력 기준인지 페이지가 판단한다. */
  onValuesChange?: (values: FinanceInput) => void;
}

const MONEY_HINTS: Partial<Record<AmountField, string>> = {
  equity: "대출을 제외하고 직접 준비할 수 있는 돈",
  desired_loan: "빌리려고 생각 중인 금액",
  expected_monthly_revenue: "한 달 매출 예상액 · 채워진 평균값은 수정할 수 있어요.",
  monthly_rent: "실제 매물의 월세를 알고 있다면 바꿔 주세요.",
};

/** 손대지 않은 0은 빈 칸으로 보여준다. 출처는 입력 라벨과 분리한다. */
function MoneyField({ name, label, hint, value, touched, onChange, badge }: {
  name: AmountField; label: string; value: number; touched: boolean; onChange: (won: number) => void;
  hint: string | undefined;
  badge?: { label: string; caveat: string };
}) {
  const describedBy = [`${name}-unit`, hint && `${name}-hint`, badge && `${name}-caveat`].filter(Boolean).join(" ");
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={`plan-${name}`}>{label}</label>
      <div className={styles.inputWrap}>
        <input id={`plan-${name}`} type="number" inputMode="numeric" name={name} aria-describedby={describedBy}
          value={touched || value !== 0 ? wonToManwon(value) : ""} placeholder="금액 입력"
          onChange={(e) => onChange(manwonToWon(Number(e.target.value) || 0))} className={styles.input} />
        <span id={`${name}-unit`} className={styles.unit}>만원</span>
      </div>
      {hint && <p id={`${name}-hint`} className={styles.hint}>{hint}</p>}
      {badge && <SourceBadge id={`${name}-caveat`} label={badge.label} caveat={badge.caveat} />}
    </div>
  );
}

function RatioField({ name, label, hint, value, onChange, badge }: {
  name: keyof FinanceInput; label: string; hint: string; value: number; onChange: (ratio: number) => void; badge?: { label: string; caveat: string };
}) {
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={`plan-${name}`}>{label}</label>
      <div className={styles.inputWrap}>
        <input id={`plan-${name}`} type="number" step="0.01" inputMode="decimal" name={name}
          aria-describedby={`${name}-hint ${name}-unit${badge ? ` ${name}-caveat` : ""}`}
          value={Math.round(value * 10000) / 100} onChange={(e) => onChange((Number(e.target.value) || 0) / 100)} className={styles.input} />
        <span id={`${name}-unit`} className={styles.unit}>%</span>
      </div>
      <p id={`${name}-hint`} className={styles.hint}>{hint}</p>
      {badge && <SourceBadge id={`${name}-caveat`} label={badge.label} caveat={badge.caveat} />}
    </div>
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
    <MoneyField key={name} name={name} label={AMOUNT_LABELS[name]} value={values[name]} touched={touched.has(name)} onChange={set(name)} badge={badges.get(name)}
      hint={name === "expected_monthly_revenue" && prefill !== null && prefill.expected_monthly_revenue.value == null
        ? "한 달 매출 예상액 · 평균값이 없어 직접 넣어 주세요."
        : MONEY_HINTS[name]} />
  );

  return (
    <form onSubmit={submit} className={styles.form} aria-label="자금 계획 입력">
      <section className={styles.card} aria-labelledby="funds-title">
        <h2 id="funds-title" className={styles.sectionTitle}><span className={styles.sectionNumber}>01</span> 나의 자금</h2>
        <p className={styles.description}>직접 준비한 돈과 대출로 마련할 돈을 나눠 적어 주세요.</p>
        <div className={styles.fieldGrid}>{money("equity")}{money("desired_loan")}</div>
      </section>
      <section className={styles.card} aria-labelledby="setup-title">
        <h2 id="setup-title" className={styles.sectionTitle}><span className={styles.sectionNumber}>02</span> 가게 준비 비용</h2>
        <p className={styles.description}>문을 열기 전에 한 번 들어가는 비용이에요.</p>
        <div className={styles.fieldGrid}>
          {money("deposit")}{money("key_money")}{money("interior_cost")}{money("equipment_cost")}
        </div>
      </section>
      <section className={styles.card} aria-labelledby="monthly-title">
        <h2 id="monthly-title" className={styles.sectionTitle}><span className={styles.sectionNumber}>03</span> 월 매출과 운영비</h2>
        <p className={styles.description}>채워진 값은 참고용 평균이에요. 내 가게에 맞게 조정해 주세요.</p>
        <div className={styles.fieldGrid}>
          {money("expected_monthly_revenue")}
          <div className={styles.field}>
            <label className={styles.label} htmlFor="plan-area">가게 면적</label>
            <div className={styles.inputWrap}>
              <input id="plan-area" type="number" inputMode="numeric" name="area_m2" value={areaM2} min={1}
                aria-describedby="area-hint area-unit" onChange={(e) => changeArea(Math.max(1, Number(e.target.value) || 1))} className={styles.input} />
              <span id="area-unit" className={styles.unit}>㎡</span>
            </div>
            <p id="area-hint" className={styles.hint}>약 {Math.round(areaM2 / 3.3058 * 10) / 10}평{rentPerM2 != null && " · 면적에 맞춰 참고 월세를 계산해요."}</p>
          </div>
          {money("monthly_rent")}{money("monthly_payroll")}{money("monthly_insurance")}
        </div>
        <details className={styles.advanced}>
          <summary>원가율·수수료·대출금리 조정</summary>
          <p className={styles.hint}>기본값으로 계산할 수 있어요. 계약 조건을 알고 있다면 수정해 주세요.</p>
          <div className={styles.ratioGrid}>
            <RatioField name="cost_ratio" label="원가율" hint="매출에서 재료·상품 구입에 쓰는 비율" value={values.cost_ratio} onChange={set("cost_ratio")} badge={badges.get("cost_ratio")} />
            <RatioField name="fee_ratio" label="수수료율" hint="매출에서 카드 결제 등에 쓰는 비율" value={values.fee_ratio} onChange={set("fee_ratio")} />
            <RatioField name="loan_rate" label="대출금리" hint="빌릴 돈에 적용할 연간 이자율" value={values.loan_rate} onChange={set("loan_rate")} badge={badges.get("loan_rate")} />
          </div>
        </details>
      </section>
      <div className={styles.submitBar}>
        <button type="submit" disabled={submitting} className={styles.primary}>
          {submitting ? "계산 중…" : "계산하기"}
        </button>
        <p className={styles.hint}>비용이 없다면 0을 입력해 주세요. 빈칸은 미확인 항목으로 남아요.</p>
      </div>
    </form>
  );
}
