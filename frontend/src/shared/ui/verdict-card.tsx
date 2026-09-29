import type { RegionIndustryVerdict, VerdictCode, VerdictSignal } from "@/shared/api/types";
import { ADVISORY_SIGNAL_KEYS, VERDICT_BASIS_BADGE, signalLabel, verdictLabel } from "@/shared/verdict";

/** 판정 → 배지 색 토큰. 🔴 --danger · 🟠 --warn · ⚪ 보조 텍스트 · 보류 테두리색 (조건 분기 대신 테이블). */
const BADGE_TOKEN: Record<VerdictCode, string> = {
  red: "var(--danger)",
  orange: "var(--warn)",
  clear: "var(--text-secondary)",
  insufficient: "var(--border)",
};

const LEVEL_LABEL: Record<VerdictSignal["level"], string> = {
  strong: "강함",
  on: "켜짐",
  off: "꺼짐",
  unavailable: "미판정",
};

const SOURCE_LABEL: Record<VerdictSignal["source"], string> = {
  store: "인허가",
  metric: "지표",
  neighborhood: "상권분석",
  tobacco: "담배소매인",
  commerce: "상권분석 집계",
  molit: "국토부 실거래가",
};

/** 참고 신호(shrinking)를 뺀 켜진 신호 최대 3개, strong 먼저. 백엔드 순서(SIGNAL_KEYS)는 같은 레벨 안에서 유지된다(안정 정렬). */
function firedSignals(signals: VerdictSignal[]): VerdictSignal[] {
  const rank: Record<VerdictSignal["level"], number> = { strong: 0, on: 1, off: 2, unavailable: 3 };
  return signals
    .filter((s) => !ADVISORY_SIGNAL_KEYS.has(s.key) && (s.level === "strong" || s.level === "on"))
    .sort((a, b) => rank[a.level] - rank[b.level])
    .slice(0, 3);
}

export function VerdictCard({ verdict, industryLabel }: { verdict: RegionIndustryVerdict; industryLabel: string }) {
  const label = verdictLabel(verdict.verdict_code);
  const fired = firedSignals(verdict.signals);
  const advisories = verdict.signals.filter((s) => ADVISORY_SIGNAL_KEYS.has(s.key) && (s.level === "on" || s.level === "strong"));
  const basisBadge = VERDICT_BASIS_BADGE[verdict.basis];
  const color = BADGE_TOKEN[verdict.verdict_code];

  return (
    <section className="mt-3 flex flex-col gap-2" aria-label="창업 경고 판정">
      <div
        role="status"
        aria-label={`${industryLabel} 판정: ${label.name}`}
        className="flex items-baseline gap-2 rounded-lg border px-3 py-2"
        style={{ borderColor: color }}
      >
        <span className="text-lg font-semibold" style={{ color }}>{label.name}</span>
        <span className="text-xs text-[var(--text-secondary)]">{label.qualifier}</span>
        {basisBadge && (
          <span title={basisBadge.description} className="rounded border border-[var(--border)] px-1 text-[10px] text-[var(--text-secondary)]">
            {basisBadge.label}
          </span>
        )}
      </div>

      {fired.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {fired.map((s) => (
            <li key={s.key} data-testid="fired-signal" className="flex items-baseline gap-1 text-xs leading-snug">
              <span className="shrink-0 font-medium text-[var(--text-primary)]">{signalLabel(s.key)}</span>
              <span className="shrink-0 text-[11px]" style={{ color: s.level === "strong" ? "var(--danger)" : "var(--warn)" }}>
                {LEVEL_LABEL[s.level]}
              </span>
              <span className="shrink-0 rounded border border-[var(--border)] px-1 text-[10px] text-[var(--text-secondary)]">
                {SOURCE_LABEL[s.source]}
              </span>
              <span className="truncate text-[var(--text-secondary)]" title={s.evidence}>{s.evidence}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">
          {verdict.verdict_code === "insufficient"
            ? "표본이 부족해 판정을 보류했습니다."
            : "서울 같은 업종 동네와 비교해 켜진 경고 신호가 없습니다."}
        </p>
      )}

      {advisories.map((s) => (
        <p key={s.key} className="text-xs text-[var(--text-secondary)]">참고: {s.evidence}</p>
      ))}

      {verdict.computed_at && <p className="text-xs tabular-nums text-[var(--text-secondary)]">산출일 <time dateTime={verdict.computed_at}>{verdict.computed_at.slice(0, 10)}</time></p>}
    </section>
  );
}
