"use client";

import { useState } from "react";
import type { VerdictCode, VerdictSignal } from "@/shared/api/types";
import { ApiError } from "@/shared/api/client";
import { industryLabel } from "@/shared/industries";
import { isVerdictIndustry, signalLabel, verdictLabel } from "@/shared/verdict";
import { useVerdict } from "../hooks/use-verdict";

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
};

/** 켜진 신호만, strong 먼저. 백엔드 순서(SIGNAL_KEYS)는 같은 레벨 안에서 유지된다(안정 정렬). */
function firedSignals(signals: VerdictSignal[]): VerdictSignal[] {
  const rank: Record<VerdictSignal["level"], number> = { strong: 0, on: 1, off: 2, unavailable: 3 };
  return signals.filter((s) => s.level === "strong" || s.level === "on").sort((a, b) => rank[a.level] - rank[b.level]);
}

/** 404(판정 없음·판정 대상 아님)는 카드를 그리지 않는다 — 학원·어린이집·배치 전 조합의 정상 동작. */
function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && (error.code === "VERDICT_NOT_FOUND" || error.code === "INDUSTRY_NOT_FOUND");
}

interface VerdictSectionProps {
  regionCode: string;
  industry: string;
}

export function VerdictSection({ regionCode, industry }: VerdictSectionProps) {
  const query = useVerdict(regionCode, industry);
  const [open, setOpen] = useState(false);

  if (!isVerdictIndustry(industry)) return null; // 편의점 등 판정 제외 업종 — 요청도 카드도 없음
  if (query.isPending) {
    return <div className="mt-4 h-16 rounded-lg bg-[var(--bg-raised)]" aria-hidden />;
  }
  if (query.isError) {
    if (isNotFound(query.error)) return null;
    return (
      <p role="alert" className="mt-4 text-xs text-[var(--danger)]">
        판정을 불러오지 못했습니다.
      </p>
    );
  }

  const verdict = query.data;
  const label = verdictLabel(verdict.verdict_code);
  const fired = firedSignals(verdict.signals);
  const color = BADGE_TOKEN[verdict.verdict_code];

  return (
    <section className="mt-4 flex flex-col gap-3" aria-label="창업 경고 판정">
      <div
        role="status"
        aria-label={`${industryLabel(industry)} 판정: ${label.name}`}
        className="flex items-baseline gap-2 rounded-lg border px-3 py-2"
        style={{ borderColor: color }}
      >
        <span className="text-lg font-semibold" style={{ color }}>{label.name}</span>
        <span className="text-xs text-[var(--text-secondary)]">{label.qualifier}</span>
      </div>

      {fired.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {fired.map((s) => (
            <li key={s.key} data-testid="fired-signal" className="text-sm leading-snug">
              <span className="font-medium text-[var(--text-primary)]">{signalLabel(s.key)}</span>
              <span className="ml-1 text-[11px]" style={{ color: s.level === "strong" ? "var(--danger)" : "var(--warn)" }}>
                {LEVEL_LABEL[s.level]}
              </span>
              <span className="ml-1 rounded border border-[var(--border)] px-1 text-[10px] text-[var(--text-secondary)]">
                {SOURCE_LABEL[s.source]}
              </span>
              <p className="text-[var(--text-secondary)]">{s.evidence}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">
          {verdict.verdict_code === "insufficient"
            ? "표본이 부족해 판정을 보류했습니다. 아래 근거에서 어떤 신호가 빠졌는지 볼 수 있습니다."
            : "서울 같은 업종 동네와 비교해 켜진 경고 신호가 없습니다."}
        </p>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="self-start text-xs text-[var(--accent)] underline-offset-2 hover:underline"
      >
        {open ? "근거 접기" : "근거 보기"}
      </button>
      {open && (
        <ul className="flex flex-col gap-1.5 border-t border-[var(--border)] pt-2 text-xs">
          {verdict.signals.map((s) => (
            <li key={s.key} data-testid="all-signal" className="flex flex-col">
              <span>
                <span className="text-[var(--text-primary)]">{signalLabel(s.key)}</span>
                <span className="ml-1 text-[var(--text-secondary)]">
                  · {LEVEL_LABEL[s.level]}
                  {s.percentile !== null && <span className="tabular-nums"> · 서울 상위 {Math.max(1, Math.round(100 - s.percentile))}%</span>}
                </span>
                <span className="ml-1 rounded border border-[var(--border)] px-1 text-[10px] text-[var(--text-secondary)]">
                  {SOURCE_LABEL[s.source]}
                </span>
              </span>
              <span className="text-[var(--text-secondary)]">{s.evidence}</span>
            </li>
          ))}
          <li className="text-[10px] text-[var(--text-secondary)]">
            상대평가 — 같은 업종의 서울 행정동 분포에서 상위 25%면 켜짐, 상위 10%면 강함. 산출 {verdict.computed_at.slice(0, 10)}
          </li>
        </ul>
      )}
    </section>
  );
}
