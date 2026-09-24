"use client";

import type { PlanProfile, PreparationStatus } from "@/shared/api/types";

/** 창업 단계 — 사용자가 직접 확인해 입력한다. **"모름"을 0·아니오로 바꾸지 않는다.**
 *  null(아직 묻지 않음)과 "unknown"(모른다고 답함)은 둘 다 미확인이지만, 전자는 물어봐야 하고
 *  후자는 상담에서 확인할 항목으로 질문 목록에 남는다. */

const FIELD =
  "rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]";

const REGISTERED_CHOICES: { value: string; label: string }[] = [
  { value: "true", label: "등록했어요" },
  { value: "false", label: "아직 전이에요" },
  { value: "unknown", label: "잘 모르겠어요" },
];

const STATUS_CHOICES: { value: PreparationStatus; label: string }[] = [
  { value: "not_started", label: "시작 전" },
  { value: "in_progress", label: "진행 중" },
  { value: "issued", label: "발급 완료" },
  { value: "unknown", label: "모름" },
];

function parseRegistered(raw: string): PlanProfile["business_registered"] {
  if (raw === "true") return true;
  if (raw === "false") return false;
  return "unknown";
}

interface ProfileFormProps {
  profile: PlanProfile;
  onChange: (patch: Partial<PlanProfile>) => void;
}

export function ProfileForm({ profile, onChange }: ProfileFormProps) {
  return (
    <section className="flex flex-col gap-4" aria-label="창업 단계">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">창업 단계</h3>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          지원 대상과 절차가 달라지는 항목입니다. 모르면 모른다고 두세요 — 상담에서 확인할 것으로 남습니다.
        </p>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-xs font-medium text-[var(--text-secondary)]">사업자등록을 하셨나요?</legend>
        <div className="flex flex-wrap gap-3">
          {REGISTERED_CHOICES.map((choice) => (
            <label key={choice.value} className="flex items-center gap-1.5 text-sm text-[var(--text-primary)]">
              <input
                type="radio"
                name="business_registered"
                value={choice.value}
                checked={String(profile.business_registered) === choice.value}
                onChange={(e) => onChange({ business_registered: parseRegistered(e.target.value) })}
              />
              {choice.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--text-secondary)]">
          개업 예정일
          <input type="date" name="planned_opening_date" value={profile.planned_opening_date ?? ""}
            onChange={(e) => onChange({ planned_opening_date: e.target.value || null })} className={FIELD} />
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--text-secondary)]">
          자금이 필요한 날
          <input type="date" name="funds_needed_by" value={profile.funds_needed_by ?? ""}
            onChange={(e) => onChange({ funds_needed_by: e.target.value || null })} className={FIELD} />
        </label>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--text-secondary)]">
          보증기관 보증서
          <select name="guarantee_status" value={profile.guarantee_status}
            onChange={(e) => onChange({ guarantee_status: e.target.value as PreparationStatus })} className={FIELD}>
            {STATUS_CHOICES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium text-[var(--text-secondary)]">
          정책자금 확인서
          <select name="policy_confirmation_status" value={profile.policy_confirmation_status}
            onChange={(e) => onChange({ policy_confirmation_status: e.target.value as PreparationStatus })} className={FIELD}>
            {STATUS_CHOICES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>
      </div>
      <p className="text-[11px] leading-snug text-[var(--text-secondary)]">
        보증기관 보증서와 정책자금 확인서는 별개 절차입니다.
      </p>
    </section>
  );
}
