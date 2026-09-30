"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { FinanceInput, PlanProfile, PlanQuestion } from "@/shared/api/types";
import { industryLabel } from "@/shared/industries";
import { fetchPlanRegion, fetchFinancePrefill, fetchFundingCandidates, fetchPlanQuestions, simulateFinance } from "../api";
import { buildDefaults, prefillBadges, type AmountField } from "../lib/form-defaults";
import { emptyDraft, recordCalculation, selectPlan, setCandidatesSeen, setProfile, setQuestions, withScope, type PlanDraft } from "../lib/plan-draft";
import { CandidateCards } from "./candidate-cards";
import { PlanComparison } from "./plan-comparison";
import { PlanForm } from "./plan-form";
import { PrepSheet } from "./prep-sheet";
import { ProfileForm } from "./profile-form";
import { QuestionList } from "./question-list";
import { ResultFigures } from "./result-figures";
import styles from "./plan-workspace.module.css";

/** /plan — 프리필 로드 → 폼 → 계산(서버) → 결과 → 최초안/현재안 비교. 초안은 화면 상태로만 둔다. */
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

  const regionInfo = useQuery({
    queryKey: ["plan-region", region, industry],
    queryFn: () => fetchPlanRegion(region!, industry!),
    enabled: !!region && !!industry,
    staleTime: 5 * 60 * 1000,
  });
  const regionName = regionInfo.data?.name ?? "선택한 동네";

  // 계획은 화면에 머무는 동안만 산다 — 다시 들어오면 빈 계획서로 시작한다(지난 계산이 남아 있으면 안 된다).
  const [draft, setDraft] = useState<PlanDraft>(() => emptyDraft(scope));
  useEffect(() => { setDraft((prev) => withScope(prev, scope)); }, [scope]);
  const update = useCallback((next: PlanDraft) => setDraft(next), []);

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
    queryKey: ["funding-candidates", industry, need, stage, region],
    queryFn: () => fetchFundingCandidates(industry, need, stage, region),
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
    <main className={styles.page} aria-label="자금 계획">
      <header className={styles.header}>
        <Link className={styles.back} href={`/map?${new URLSearchParams({ region, industry })}`}>← 상권 탐색으로</Link>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>자금 계획</h1>
          <p className={styles.context}><span>{regionName}</span><span aria-hidden="true">·</span><span>{industryLabel(industry)}</span></p>
        </div>
        <p className={styles.intro}>가게를 열려면 얼마가 필요할까요? 준비 비용과 매달 나갈 돈을 함께 살펴보세요.</p>
        <ol className={styles.steps} aria-label="자금 계획 순서">
          <li aria-current={!shown || stale ? "step" : undefined}><span>1</span> 비용 입력</li>
          <li aria-current={shown && !stale && !prepOpen ? "step" : undefined}><span>2</span> 필요 자금 확인</li>
          <li aria-current={prepOpen && canPrep ? "step" : undefined}><span>3</span> 상담 준비</li>
        </ol>
      </header>
      <div className={styles.workspace}>
        <section aria-label="입력">
          {prefill.isPending && <p role="status" className={styles.status}>참고할 평균 매출과 임대료를 불러오고 있어요…</p>}
          {prefill.isError && <p role="alert" className="mb-4 text-xs text-[var(--danger)]">실측값을 불러오지 못했습니다. 직접 입력해도 계산은 됩니다.</p>}
          <PlanForm defaults={defaults.values} prefill={prefill.data ?? null} submitting={calc.isPending}
            onSubmit={(values, unconfirmed) => calc.mutate({ values, unconfirmed })} onValuesChange={onValuesChange} />
          {calc.isError && <p role="alert" className="mt-3 text-xs text-[var(--danger)]">계산에 실패했습니다. 원가율과 수수료율의 합이 100% 미만인지 확인하세요.</p>}
        </section>
        <aside className={styles.sidebar} aria-label="계획 요약">
          {shown ? <div className={styles.card}>
            {stale && <p role="status" className={styles.status}>입력값이 바뀌었어요. 다시 계산하면 결과에 반영됩니다.</p>}
            <ResultFigures result={shown.result} unconfirmed={shown.unconfirmed} />
            <details className={`${styles.disclosure} mt-6`}>
              <summary>최초 계획과 비교하기</summary>
              <div><PlanComparison draft={draft} stale={stale} onSelect={(kind) => update(selectPlan(draft, kind))}
                onReasonChange={(reason) => update({ ...draft, change_reason: reason })} /></div>
            </details>
          </div> : (
            <div className={`${styles.card} ${styles.empty}`}>
              <p className={styles.eyebrow}>나의 자금 계획서</p>
              <h2>얼마를 더 준비해야 할지<br />함께 확인해 볼까요?</h2>
              <p>비용을 입력하고 계산하면 필요한 자금과 매출 목표를 정리해 드려요.</p>
              <dl className={styles.previewList}>
                <div><dt>총 준비자금</dt><dd>계산 후 확인</dd></div>
                <div><dt>추가로 마련할 돈</dt><dd>계산 후 확인</dd></div>
                <div><dt>손익분기 월매출</dt><dd>계산 후 확인</dd></div>
              </dl>
            </div>
          )}
          {shown && !prepOpen && (
            <button type="button" onClick={() => setPrepOpen(true)} disabled={!canPrep} className={styles.primary}>
              조달·상담 준비 →
            </button>
          )}
          <p className={styles.note}>자동으로 채워진 값은 참고용이에요. 실제 견적이나 계약 금액을 알면 바꿔서 계산해 보세요.</p>
        </aside>
      </div>
      {prepOpen && canPrep && (
        <section className={styles.prep} aria-label="조달과 상담 준비">
          <h2 className={styles.sectionTitle}>상담 준비</h2>
          <p className={styles.hint}>계산한 계획을 바탕으로 지원 공고와 상담에서 확인할 내용을 정리해요.</p>
          <div className={styles.prepGrid}>
            <div className={styles.card}><ProfileForm profile={draft.profile} onChange={(patch: Partial<PlanProfile>) => update(setProfile(draft, patch))} /></div>
            <div className={styles.card}><CandidateCards candidates={candidates.data?.candidates ?? []} need={need}
              isPending={candidates.isPending} isError={candidates.isError} /></div>
          </div>
          <QuestionList questions={draft.questions} isPending={questions.isPending && draft.questions.length === 0}
            isError={questions.isError} onChange={(next: PlanQuestion[]) => update(setQuestions(draft, next))} />
          <PrepSheet draft={draft} regionName={regionName} industryLabel={industryLabel(industry)}
            candidates={candidates.data?.candidates ?? []} caveats={caveats} />
        </section>
      )}
    </main>
  );
}
