import type { ReportFacts } from "@/shared/api/types";

export function FundingCards({ candidates }: { candidates?: ReportFacts["funding_candidates"] }) {
  if (!Array.isArray(candidates) || candidates.length === 0) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  return <ul className="grid gap-3 sm:grid-cols-2">
    {candidates.slice(0, 5).map((candidate, index) => <li key={candidate.program_id ?? candidate.id ?? index} className="min-w-0 space-y-2 rounded-lg border border-[var(--border)] p-4">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">{candidate.title || "제목 없음"}</h3>
      <p className="text-xs text-[var(--text-secondary)]">{candidate.org || "기관 정보 없음"}</p>
      <p className="truncate text-sm text-[var(--text-secondary)]" title={candidate.summary || candidate.why || "요약 없음"}>{candidate.summary || candidate.why || "요약 없음"}</p>
      {candidate.target && <p className="text-xs text-[var(--text-secondary)]">대상: {candidate.target}</p>}
      {candidate.url && /^https?:\/\//i.test(candidate.url) && <a href={candidate.url} target="_blank" rel="noopener" className="text-sm text-[var(--accent)] underline">원문</a>}
    </li>)}
  </ul>;
}
