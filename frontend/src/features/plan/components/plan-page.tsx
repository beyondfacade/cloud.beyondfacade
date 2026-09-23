"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { FinanceInput } from "@/shared/api/types";
import { industryLabel } from "@/shared/industries";
import { fetchFinancePrefill, simulateFinance } from "../api";
import { buildDefaults, type AmountField } from "../lib/form-defaults";
import { emptyDraft, loadDraft, recordCalculation, saveDraft, selectPlan, withScope, type PlanDraft } from "../lib/plan-draft";
import { PlanComparison } from "./plan-comparison";
import { PlanForm } from "./plan-form";
import { ResultFigures } from "./result-figures";

/** /plan — 프리필 로드 → 폼 → 계산(서버) → 결과 → 최초안/현재안 비교. 초안은 sessionStorage에 산다. */
export function PlanPage() {
  const searchParams = useSearchParams();
  const region = searchParams.get("region");
  const industry = searchParams.get("industry");
  const budget = searchParams.get("budget");
  const scope = useMemo(() => ({ region, industry }), [region, industry]);

  const prefill = useQuery({
    queryKey: ["finance-prefill", region, industry],
    queryFn: () => fetchFinancePrefill(region!, industry!),
    enabled: !!region && !!industry,
  });

  const [draft, setDraft] = useState<PlanDraft>(() => emptyDraft(scope));
  useEffect(() => { setDraft(withScope(loadDraft() ?? emptyDraft(scope), scope)); }, [scope]);
  const update = useCallback((next: PlanDraft) => { setDraft(next); saveDraft(next); }, []);

  const defaults = useMemo(() => buildDefaults({ budget, prefill: prefill.data ?? null }), [budget, prefill.data]);

  // 마지막으로 계산한 입력과 지금 폼 값이 다르면 결과는 이전 입력 기준이다.
  const [lastInput, setLastInput] = useState<string | null>(null);
  const [liveInput, setLiveInput] = useState<string | null>(null);
  const stale = lastInput !== null && liveInput !== null && lastInput !== liveInput;
  const onValuesChange = useCallback((v: FinanceInput) => setLiveInput(JSON.stringify(v)), []);

  const calc = useMutation({
    mutationFn: ({ values }: { values: FinanceInput; unconfirmed: AmountField[] }) => simulateFinance(values),
    onSuccess: (result, { values, unconfirmed }) => {
      setLastInput(JSON.stringify(values));
      update(recordCalculation(draft, values, result, unconfirmed));
    },
  });

  const shown = draft.selected ? draft[draft.selected] : null;

  if (!region || !industry) {
    return <main className="mx-auto max-w-3xl px-4 py-10"><p className="text-sm text-[var(--text-secondary)]">지도에서 동네와 업종을 고른 뒤 "자금 계획"으로 들어와 주세요.</p></main>;
  }

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-10 px-4 py-10" aria-label="자금 계획">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--accent)]">SEOUL COMMERCIAL ATLAS / PLAN</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">그래서 얼마가 필요한가</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          <span className="tabular-nums">{region}</span> · {industryLabel(industry)} — 채워진 값은 실측·공시에서 왔습니다. 출처를 보고 고친 뒤 계산하세요.
        </p>
      </header>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <section aria-label="입력">
          {prefill.isPending && <p role="status" className="mb-4 text-xs text-[var(--text-secondary)]">이 동네의 실측값을 불러오는 중…</p>}
          {prefill.isError && <p role="alert" className="mb-4 text-xs text-[var(--danger)]">실측값을 불러오지 못했습니다. 직접 입력해도 계산은 됩니다.</p>}
          <PlanForm defaults={defaults.values} prefill={prefill.data ?? null} submitting={calc.isPending}
            onSubmit={(values, unconfirmed) => calc.mutate({ values, unconfirmed })} onValuesChange={onValuesChange} />
          {calc.isError && <p role="alert" className="mt-3 text-xs text-[var(--danger)]">계산에 실패했습니다. 원가율과 수수료율의 합이 100% 미만인지 확인하세요.</p>}
        </section>
        <div className="flex flex-col gap-10">
          {shown ? <ResultFigures result={shown.result} /> : (
            <p className="text-sm text-[var(--text-secondary)]">계산하면 자기자본 외 조달 필요 금액이 여기에 나옵니다.</p>
          )}
          <PlanComparison draft={draft} stale={stale} onSelect={(kind) => update(selectPlan(draft, kind))}
            onReasonChange={(reason) => update({ ...draft, change_reason: reason })} />
        </div>
      </div>
    </main>
  );
}
