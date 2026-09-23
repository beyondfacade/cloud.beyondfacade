import type { FinanceInput } from "@/shared/api/types";
import { AMOUNT_LABELS, type AmountField } from "../lib/form-defaults";
import { formatManwon } from "../lib/money";
import type { PlanDraft, PlanKind, PlanSnapshot } from "../lib/plan-draft";

interface PlanComparisonProps {
  draft: PlanDraft;
  /** 수정 후 아직 계산하지 않은 상태 — 이전 결과로 안을 고르지 못하게 잠근다. */
  stale: boolean;
  onSelect: (kind: PlanKind) => void;
  onReasonChange: (reason: string) => void;
}

type Row =
  | { from: "input"; key: keyof FinanceInput; label: string }
  | { from: "result"; key: "external_funding_need" | "total_required_funds" | "bep_revenue"; label: string };

const ROWS: Row[] = [
  { from: "input", key: "monthly_rent", label: AMOUNT_LABELS.monthly_rent },
  { from: "input", key: "deposit", label: AMOUNT_LABELS.deposit },
  { from: "input", key: "interior_cost", label: AMOUNT_LABELS.interior_cost },
  { from: "input", key: "expected_monthly_revenue", label: AMOUNT_LABELS.expected_monthly_revenue },
  { from: "input", key: "desired_loan", label: AMOUNT_LABELS.desired_loan },
  { from: "result", key: "total_required_funds", label: "총 준비자금" },
  { from: "result", key: "external_funding_need", label: "자기자본 외 조달 필요" },
  { from: "result", key: "bep_revenue", label: "손익분기 월매출" },
];

function cell(plan: PlanSnapshot | null, row: Row): string {
  if (!plan) return "—";
  return formatManwon(row.from === "input" ? plan.input[row.key] : plan.result[row.key]);
}

/** 최초안 vs 현재안. 사용자가 상담할 안을 고르고 변경 이유를 직접 쓴다 — 추정하지 않는다. */
export function PlanComparison({ draft, stale, onSelect, onReasonChange }: PlanComparisonProps) {
  if (!draft.baseline) return null;
  const kinds: PlanKind[] = ["baseline", "current"];
  const unconfirmed = (draft.selected ? draft[draft.selected]?.unconfirmed : []) ?? [];
  return (
    <section className="flex flex-col gap-4" aria-label="최초안과 현재안 비교">
      {stale && (
        <p role="status" className="rounded-md border border-[var(--warn)] px-3 py-2 text-xs text-[var(--text-primary)]">
          아래 결과는 이전 입력 기준이에요. 계산하기를 눌러야 현재안이 갱신되고 안을 고를 수 있습니다.
        </p>
      )}
      <table className="w-full text-sm" aria-label="계획 비교표">
        <thead className="text-xs text-[var(--text-secondary)]">
          <tr><th className="py-1 text-left font-medium">항목</th><th className="text-right font-medium">최초안</th><th className="text-right font-medium">현재안</th></tr>
        </thead>
        <tbody className="tabular-nums">
          {ROWS.map((row) => (
            <tr key={row.key} className={`border-t border-[var(--border)] ${row.from === "result" ? "font-medium" : ""}`}>
              <td className="py-2">{row.label}</td>
              <td className="text-right">{cell(draft.baseline, row)}</td>
              <td className="text-right">{cell(draft.current, row)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <fieldset className="flex gap-4" disabled={stale}>
        <legend className="mb-2 text-xs font-medium text-[var(--text-secondary)]">상담할 안 선택</legend>
        {kinds.map((kind) => (
          <label key={kind} className="flex items-center gap-2 text-sm">
            <input type="radio" name="selected-plan" value={kind} checked={draft.selected === kind} disabled={stale || draft[kind] === null} onChange={() => onSelect(kind)} />
            {kind === "baseline" ? "최초안" : "현재안"}
          </label>
        ))}
      </fieldset>
      {unconfirmed.length > 0 && (
        <p className="text-xs text-[var(--text-secondary)]">
          입력하지 않아 0원으로 계산한 항목: {unconfirmed.map((f: AmountField) => AMOUNT_LABELS[f]).join(" · ")} — 유효한 0원인지 확인이 필요합니다.
        </p>
      )}
      <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--text-secondary)]">
        변경 이유 (상담 준비자료에 그대로 실립니다)
        <textarea value={draft.change_reason} onChange={(e) => onReasonChange(e.target.value)} rows={3}
          placeholder="예: 월세를 250만에서 100만으로 낮춘 매물로 검토 중"
          className="rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]" />
      </label>
    </section>
  );
}
