"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { FinanceInput, PlanProfile, PlanQuestion } from "@/shared/api/types";
import { industryLabel } from "@/shared/industries";
import { fetchFinancePrefill, fetchFundingCandidates, fetchPlanQuestions, simulateFinance } from "../api";
import { buildDefaults, prefillBadges, type AmountField } from "../lib/form-defaults";
import { emptyDraft, loadDraft, recordCalculation, saveDraft, selectPlan, setCandidatesSeen, setProfile, setQuestions, withScope, type PlanDraft } from "../lib/plan-draft";
import { CandidateCards } from "./candidate-cards";
import { PlanComparison } from "./plan-comparison";
import { PlanForm } from "./plan-form";
import { PrepSheet } from "./prep-sheet";
import { ProfileForm } from "./profile-form";
import { QuestionList } from "./question-list";
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

  // ⑤ 조달·준비 — 계산이 끝나고 안을 고른 뒤에만 연다. 그 전에는 채울 재료가 없다.
  const [prepOpen, setPrepOpen] = useState(false);
  const canPrep = shown !== null && !stale;
  const need = shown?.result.external_funding_need ?? null;
  const stage = draft.profile.business_registered === true ? "registered" : "pre";

  const candidates = useQuery({
    queryKey: ["funding-candidates", industry, need, stage],
    queryFn: () => fetchFundingCandidates(industry, need, stage),
    enabled: prepOpen && canPrep,
  });

  // 서버 초안은 한 번만 받는다 — 사용자가 고친 편집본이 정본이라 다시 덮지 않는다.
  const questionsAsked = useRef(false);
  const questions = useQuery({
    queryKey: ["plan-questions", draft.selected, need, stage, candidates.data?.candidates.length ?? 0],
    queryFn: () =>
      fetchPlanQuestions({
        input: shown!.input,
        unconfirmed: shown!.unconfirmed,
        prefilled: prefillBadges(prefill.data ?? null).map((b) => String(b.field)),
        candidate_titles: (candidates.data?.candidates ?? []).map((c) => c.title),
        profile: {
          // 화면의 "unknown"은 와이어에서 null — 서버 계약이 bool|null만 받는다.
          business_registered: draft.profile.business_registered === "unknown" ? null : draft.profile.business_registered,
          guarantee_status: draft.profile.guarantee_status,
          policy_confirmation_status: draft.profile.policy_confirmation_status,
        },
        change_reason: draft.change_reason,
      }),
    enabled: prepOpen && canPrep && !questionsAsked.current,
  });

  useEffect(() => {
    const seen = candidates.data?.candidates.map((c) => c.title);
    if (seen && seen.join("|") !== draft.candidates_seen.join("|")) update(setCandidatesSeen(draft, seen));
  }, [candidates.data, draft, update]);

  useEffect(() => {
    if (questions.data && !questionsAsked.current) {
      questionsAsked.current = true;
      update(setQuestions(draft, questions.data));
    }
  }, [questions.data, draft, update]);

  const caveats = useMemo(() => prefillBadges(prefill.data ?? null).map((b) => b.caveat), [prefill.data]);

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
          {shown && !prepOpen && (
            <button type="button" onClick={() => setPrepOpen(true)} disabled={!canPrep}
              className="w-fit rounded-lg bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-[var(--accent-fg)] disabled:opacity-40">
              조달·상담 준비 →
            </button>
          )}
        </div>
      </div>
      {prepOpen && canPrep && (
        <section className="flex flex-col gap-10 border-t border-[var(--border)] pt-10" aria-label="조달과 상담 준비">
          <div className="grid gap-10 lg:grid-cols-2">
            <ProfileForm profile={draft.profile} onChange={(patch: Partial<PlanProfile>) => update(setProfile(draft, patch))} />
            <CandidateCards candidates={candidates.data?.candidates ?? []} need={need}
              isPending={candidates.isPending} isError={candidates.isError} />
          </div>
          <QuestionList questions={draft.questions} isPending={questions.isPending && draft.questions.length === 0}
            isError={questions.isError} onChange={(next: PlanQuestion[]) => update(setQuestions(draft, next))} />
          <PrepSheet draft={draft} regionName={region} industryLabel={industryLabel(industry)}
            candidates={candidates.data?.candidates ?? []} caveats={caveats} />
        </section>
      )}
    </main>
  );
}
