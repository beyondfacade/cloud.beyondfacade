import type { FinanceInput, FinanceResult, PlanProfile, PlanQuestion } from "@/shared/api/types";
import type { AmountField } from "./form-defaults";

/** 화면에 머무는 동안의 한 계획. 저장하지 않는다 — 다시 들어오면 지난 계산 없이 새로 시작한다.
 *  대구 `consultation-draft.ts` 이식. 상담 프로필·질문·본 후보를 함께 든다. */
export type PlanKind = "baseline" | "current";

export interface PlanSnapshot {
  input: FinanceInput;
  result: FinanceResult;
  /** 사용자가 한 번도 입력하지 않은 금액 필드 — 유효한 0원과 구분하기 위한 기록. */
  unconfirmed: AmountField[];
}

export interface PlanScope {
  region: string | null;
  industry: string | null;
}

export interface PlanDraft extends PlanScope {
  /** 최초안 — 첫 성공 계산으로 고정한다. */
  baseline: PlanSnapshot | null;
  /** 현재안 — 이후 계산이 갱신한다. */
  current: PlanSnapshot | null;
  selected: PlanKind | null;
  /** 사용자가 직접 쓴 변경 이유 — 추정하지 않는다. */
  change_reason: string;
  /** 창업 단계. null은 아직 묻지 않은 것, "unknown"은 모른다고 답한 것 — 0·아니오로 바꾸지 않는다. */
  profile: PlanProfile;
  /** 질문 **편집본**. 서버 초안을 사용자가 고친 결과가 정본이다 — 다시 불러도 덮지 않는다. */
  questions: PlanQuestion[];
  /** 화면에 띄운 후보 공고 제목 — 질문 생성 요청에 실어 보낸다(finance BC가 funding BC를 직접 읽지 않는다). */
  candidates_seen: string[];
}

export const EMPTY_PROFILE: PlanProfile = {
  business_registered: null,
  planned_opening_date: null,
  funds_needed_by: null,
  guarantee_status: "unknown",
  policy_confirmation_status: "unknown",
};

export function emptyDraft(scope: PlanScope): PlanDraft {
  return {
    region: scope.region, industry: scope.industry,
    baseline: null, current: null, selected: null, change_reason: "",
    profile: { ...EMPTY_PROFILE }, questions: [], candidates_seen: [],
  };
}

/** 첫 성공 계산은 최초안으로 고정하고, 이후 계산은 현재안을 갱신한다.
 *  방금 계산한 안을 선택안으로 둬 선택안이 늘 유효한 계산안을 가리키게 한다. */
export function recordCalculation(draft: PlanDraft, input: FinanceInput, result: FinanceResult, unconfirmed: AmountField[] = []): PlanDraft {
  const snapshot: PlanSnapshot = { input: { ...input }, result: { ...result }, unconfirmed: [...unconfirmed] };
  return draft.baseline === null
    ? { ...draft, baseline: snapshot, selected: "baseline" }
    : { ...draft, current: snapshot, selected: "current" };
}

/** 없는 계산안은 선택하지 않는다. */
export function selectPlan(draft: PlanDraft, kind: PlanKind): PlanDraft {
  return draft[kind] === null ? draft : { ...draft, selected: kind };
}

export function selectedPlan(draft: PlanDraft): PlanSnapshot | null {
  return draft.selected === null ? null : draft[draft.selected];
}

/** 지역·업종이 바뀌면 비교 대상이 달라지므로 이전 결과·선택을 무효화한다. */
export function withScope(draft: PlanDraft, scope: PlanScope): PlanDraft {
  if (draft.region === scope.region && draft.industry === scope.industry) return draft;
  // 동네·업종이 바뀌면 후보와 질문도 달라진다. 사용자가 쓴 변경 이유와 창업 단계는 사람의 사실이라 남긴다.
  return { ...emptyDraft(scope), change_reason: draft.change_reason, profile: draft.profile };
}

/** 창업 단계 갱신 — 한 항목만 바꾼다. */
export function setProfile(draft: PlanDraft, patch: Partial<PlanProfile>): PlanDraft {
  return { ...draft, profile: { ...draft.profile, ...patch } };
}

/** 질문 편집본 교체. 서버 초안을 처음 받을 때와 사용자가 고칠 때 모두 여기를 지난다. */
export function setQuestions(draft: PlanDraft, questions: PlanQuestion[]): PlanDraft {
  return { ...draft, questions: [...questions] };
}

export function setCandidatesSeen(draft: PlanDraft, titles: string[]): PlanDraft {
  return { ...draft, candidates_seen: [...titles] };
}
