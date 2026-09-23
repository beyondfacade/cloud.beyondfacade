import type { FinanceInput, FinanceResult } from "@/shared/api/types";
import type { AmountField } from "./form-defaults";

/** 한 탭의 한 계획을 보관한다. 장기 저장이 아니다 — 로그인이 없는데 서버 테이블은 이르다.
 *  대구 `consultation-draft.ts` 이식. 상담 프로필은 T4에서 더한다. */
export const DRAFT_KEY = "beyondfacade.plan.v1";
const VERSION = 1;

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
  version: number;
  /** 최초안 — 첫 성공 계산으로 고정한다. */
  baseline: PlanSnapshot | null;
  /** 현재안 — 이후 계산이 갱신한다. */
  current: PlanSnapshot | null;
  selected: PlanKind | null;
  /** 사용자가 직접 쓴 변경 이유 — 추정하지 않는다. */
  change_reason: string;
}

const AMOUNT_FIELDS: (keyof FinanceInput)[] = [
  "deposit", "key_money", "interior_cost", "equipment_cost",
  "monthly_rent", "monthly_payroll", "monthly_insurance",
  "equity", "desired_loan", "expected_monthly_revenue",
];
const RATIO_FIELDS: (keyof FinanceInput)[] = ["cost_ratio", "fee_ratio", "loan_rate"];

export function emptyDraft(scope: PlanScope): PlanDraft {
  return { version: VERSION, region: scope.region, industry: scope.industry, baseline: null, current: null, selected: null, change_reason: "" };
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
  return { ...emptyDraft(scope), change_reason: draft.change_reason };
}

export function saveDraft(draft: PlanDraft): void {
  try {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // 저장 실패는 계산을 막지 않는다.
  }
}

/** 구조·금액·비율을 검증해 복원한다. 어긋나면 null — 다시 입력하도록 안내한다. */
export function loadDraft(): PlanDraft | null {
  let raw: string | null;
  try {
    raw = sessionStorage.getItem(DRAFT_KEY);
  } catch {
    return null;
  }
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as PlanDraft;
    return isValidDraft(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isValidDraft(draft: PlanDraft): boolean {
  if (draft?.version !== VERSION) return false;
  if (!isValidPlan(draft.baseline) || !isValidPlan(draft.current)) return false;
  if (draft.selected !== null && draft[draft.selected] == null) return false;
  return true;
}

function isValidPlan(plan: PlanSnapshot | null): boolean {
  if (plan == null) return true;
  const { input, result } = plan;
  if (input == null || result == null) return false;
  if (!AMOUNT_FIELDS.every((f) => Number.isFinite(input[f]) && input[f] >= 0)) return false;
  if (!RATIO_FIELDS.every((f) => Number.isFinite(input[f]) && input[f] >= 0 && input[f] < 1)) return false;
  // 백엔드 422와 같은 규칙 — 변동비율 ≥ 1이면 BEP가 성립하지 않는다.
  if (input.cost_ratio + input.fee_ratio >= 1) return false;
  return Number.isFinite(result.external_funding_need) && Number.isFinite(result.total_required_funds);
}
