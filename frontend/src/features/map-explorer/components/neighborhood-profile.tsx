"use client";

import type { RegionProfile } from "@/shared/api/types";
import { neighborhoodTypeLabel, phasesNarrative, timeLabelSentence } from "@/shared/neighborhood";
import { useRegionProfile } from "../hooks/use-region-profile";

/** '20262' → '2026년 2분기'. */
function formatQuarter(yearQuarter: string): string {
  return `${yearQuarter.slice(0, 4)}년 ${yearQuarter.slice(4)}분기`;
}

/** 결측은 0이 아니다 — 직장인구가 없는 11개 동을 0으로 읽으면 주거형으로 오해한다. */
function orMissing(value: number | null, format: (v: number) => string): string {
  return value === null ? "집계 없음" : format(value);
}

function EvidenceRow({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-2 text-sm">
      <span className="text-[var(--text-secondary)]">{label}</span>
      <span className="text-right">
        <span className="tabular-nums text-[var(--text-primary)]">{value}</span>
        {hint && <span className="ml-1.5 text-xs text-[var(--text-secondary)]">{hint}</span>}
      </span>
    </li>
  );
}

export function NeighborhoodProfileBody({ profile }: { profile: RegionProfile }) {
  const type = neighborhoodTypeLabel(profile.neighborhood_type);
  // 정점→바닥 서사가 없는 조합이면 시간대 라벨 문장으로 물러선다 (분류 문서 §6-4)
  const narrative =
    phasesNarrative(profile.peak_block, profile.trough_block) ?? timeLabelSentence(profile.time_label);

  return (
    <>
      <div className="flex flex-col gap-1 border-t border-[var(--border)] pt-3">
        <span
          className="text-xl font-medium tracking-tight text-[var(--text-primary)]"
          title={type.tooltip}
        >
          {type.name}
        </span>
        <span className="text-xs text-[var(--text-secondary)]">({type.qualifier})</span>
      </div>

      <p className="text-sm leading-relaxed text-[var(--text-primary)]">{profile.type_reason}</p>

      {narrative && (
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{narrative}</p>
      )}

      <ul
        className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]"
        aria-label="판정 근거 수치"
      >
        <EvidenceRow
          label="직장인구 ÷ 상주인구"
          value={orMissing(profile.worker_resident_ratio, (v) => `${v.toFixed(1)}배`)}
        />
        <EvidenceRow
          label="주말 유동"
          value={orMissing(profile.weekend_index, (v) => `${v.toFixed(2)}배`)}
          hint="평일 대비"
        />
        <EvidenceRow
          label="심야 체류"
          value={orMissing(profile.night_index, (v) => v.toFixed(2))}
          hint="1.00 = 하루 평균"
        />
        <EvidenceRow
          label="음식·유흥 결제 비중"
          value={orMissing(profile.fnb_share, (v) => `${(v * 100).toFixed(1)}%`)}
        />
        <EvidenceRow
          label="상주인구"
          value={orMissing(profile.resident_total, (v) => `${v.toLocaleString("ko-KR")}명`)}
        />
      </ul>

      <p className="text-xs tabular-nums text-[var(--text-secondary)]">
        기준 {formatQuarter(profile.year_quarter)} · 최근 4분기 평균으로 판정
      </p>
    </>
  );
}

/** 패널 ① 어떤 동네인가 — 창업자의 첫 질문이라 맨 위에 온다. 조회 키는 ②(하루 흐름)와 같아 요청은 한 번이다. */
export function NeighborhoodProfileSection({ regionCode }: { regionCode: string }) {
  const profile = useRegionProfile(regionCode);

  return (
    <section className="mt-7 flex flex-col gap-3" aria-label="동네 유형">
      <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">동네 유형</h3>
      {profile.isPending && (
        <div className="h-40 rounded bg-[var(--bg-raised)]" role="status" aria-label="불러오는 중" />
      )}
      {profile.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          동네 유형을 불러오지 못했습니다.
        </p>
      )}
      {profile.data && <NeighborhoodProfileBody profile={profile.data} />}
    </section>
  );
}
