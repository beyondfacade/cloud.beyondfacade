import type { ReportFacts, VerdictSignalLevel } from "@/shared/api/types";
import { ADVISORY_SIGNAL_KEYS, signalLabel } from "@/shared/verdict";
import { availableFact } from "../../lib/available-fact";

const COLORS: Record<VerdictSignalLevel, string> = {
  strong: "var(--danger)", on: "var(--warn)", off: "var(--text-secondary)", unavailable: "var(--border)",
};

export function SignalBars({ verdict }: { verdict?: ReportFacts["verdict"] }) {
  const data = availableFact(verdict);
  if (!data) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  return (
    <div role="group" aria-label="신호 백분위" className="space-y-3">
      <p className="text-xs text-[var(--text-secondary)]">서울 같은 업종 대비 경고 백분위 (0~100)</p>
      <div role="group" className="relative h-4 text-xs tabular-nums text-[var(--text-secondary)]" aria-label="백분위 기준선">
        {[75, 90].map((n) => <span key={n} className="absolute -translate-x-1/2" style={{ left: `${n}%` }}>{n}</span>)}
      </div>
      <ul className="space-y-3">
        {data.signals.map((signal) => {
          const { key, percentile: value } = signal;
          const percentile = typeof value === "number" && Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : null;
          const color = COLORS[signal.level];
          return (
            <li key={key}>
              <div className="mb-1 flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                <span>{signalLabel(key)}</span>
                {ADVISORY_SIGNAL_KEYS.has(key) && <span>참고</span>}
                <span className="ml-auto tabular-nums">{percentile === null ? "미판정" : `${percentile}백분위`}</span>
              </div>
              <div className="relative h-2 rounded border border-[var(--border)] bg-[var(--bg-raised)]"
                role={percentile === null ? undefined : "meter"} aria-label={signalLabel(key)}
                aria-valuemin={percentile === null ? undefined : 0} aria-valuemax={percentile === null ? undefined : 100} aria-valuenow={percentile ?? undefined}>
                {percentile !== null && <div className="h-full rounded" style={{ width: `${percentile}%`, backgroundColor: color }} />}
                {[75, 90].map((n) => <span key={n} aria-hidden className="absolute -top-1 h-4 border-l border-dashed border-[var(--text-secondary)]" style={{ left: `${n}%` }} />)}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
