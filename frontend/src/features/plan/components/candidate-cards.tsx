"use client";

import type { FundingCandidate } from "@/shared/api/types";
import { formatManwon } from "../lib/money";

/** 후보 공고 — **자격 확정이 아니라 해당 가능성**이다. 그 고지를 목록 상단에 고정한다.
 *  업종·금액은 필터에 쓰이지 않고 문장용으로 되돌아온 값이다(공고에 구조화돼 있지 않다). */
export function CandidateCards({
  candidates,
  need,
  isPending,
  isError,
}: {
  candidates: FundingCandidate[];
  need: number | null;
  isPending?: boolean;
  isError?: boolean;
}) {
  return (
    <section className="flex flex-col gap-3" aria-label="지원 공고 후보">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">찾아본 지원 공고</h3>
        <p className="mt-1 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-2 text-xs text-[var(--text-secondary)]">
          자격 확정이 아니라 <strong className="font-medium text-[var(--text-primary)]">해당 가능성이 있는 공고</strong>입니다.
          신청 자격·한도는 원문에서 확인하세요.
          {need != null && ` 조달 필요 ${formatManwon(need)} 기준으로 찾았습니다.`}
        </p>
      </div>

      {isPending && <div role="status" aria-label="불러오는 중" className="h-24 rounded bg-[var(--bg-raised)]" />}
      {isError && <p role="alert" className="text-sm text-[var(--danger)]">공고를 불러오지 못했습니다.</p>}
      {!isPending && !isError && candidates.length === 0 && (
        <p className="text-sm text-[var(--text-secondary)]">지금 해당하는 공고를 찾지 못했습니다.</p>
      )}

      <ul className="flex flex-col gap-2">
        {candidates.map((c) => (
          <li key={c.program_id} className="rounded-lg border border-[var(--border)] p-3">
            <a href={c.url} target="_blank" rel="noreferrer"
              className="text-sm font-medium text-[var(--text-primary)] underline decoration-[var(--border)] underline-offset-2 hover:decoration-[var(--accent)]">
              {c.title}
            </a>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              {c.org} · {c.apply_period}
            </p>
            <p className="mt-1 text-[11px] text-[var(--text-secondary)]">{c.why}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
