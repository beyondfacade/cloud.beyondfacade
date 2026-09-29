/** 판정 코드·신호 키의 표기 어휘. 코드는 API 계약 값이라 영문 유지, 화면엔 라벨만.
 *  판정은 백엔드 verdict 배치가 하고 여기는 사람이 읽는 말로 옮기기만 한다. 🟢 추천은 없다(HANDOFF §0-2).
 *  지도 범례·사이드패널 카드가 함께 쓰므로 shared에 둔다. */
import type { VerdictBasis, VerdictCode, VerdictSignalKey } from "@/shared/api/types";
import { INDUSTRIES } from "@/shared/industries";

export const VERDICT_CODES = ["red", "orange", "clear", "insufficient"] as const satisfies readonly VerdictCode[];

export interface VerdictLabel {
  name: string;
  qualifier: string;
}

const LABELS: Record<VerdictCode, VerdictLabel> = {
  red: { name: "비추천", qualifier: "강한 경고 신호 2개 이상" },
  orange: { name: "조건부", qualifier: "경고 신호 1개 이상" },
  clear: { name: "경고 없음", qualifier: "켜진 신호 없음" },
  insufficient: { name: "판정 보류", qualifier: "표본 부족 — 판정 가능한 신호 2개 미만" },
};

export function verdictLabel(code: string): VerdictLabel {
  return LABELS[code as VerdictCode] ?? { name: code, qualifier: "분류 없음" };
}

export const SIGNAL_LABELS: Record<VerdictSignalKey, string> = {
  net_outflow: "순유출",
  survival_cliff: "생존 절벽",
  early_closure: "조기 폐업",
  saturation: "포화",
  shrinking: "상권 축소",
  closure_rate: "폐업률",
  tobacco_gap: "담배권 빈자리",
  trade_per_office: "사무소당 거래",
};

export function signalLabel(key: string): string {
  return SIGNAL_LABELS[key as VerdictSignalKey] ?? key;
}

/** 편의점·부동산은 9/29 업종 특화 원천으로 재포함 게이트를 심사했으나 경고 lift 1.10배 기준에 미달(편의점 1.00×·부동산 1.04×) — 그대로 제외.
 *  백엔드 `EXCLUDED_INDUSTRIES` 중 프론트 `INDUSTRIES`(14)에 남아 있는 것만 여기 둔다. */
export const VERDICT_EXCLUDED_INDUSTRIES: ReadonlySet<string> = new Set(["convenience_store", "real_estate"]);

/** 백엔드 `ADVISORY_SIGNAL_KEYS` 미러 — 상권 축소(무신호)·담배권 빈자리(진입 가능성) 등은 평가·표시만. */
export const ADVISORY_SIGNAL_KEYS: ReadonlySet<VerdictSignalKey> = new Set(["shrinking", "tobacco_gap", "trade_per_office"]);

/** 판정 원천 배지 — 인허가는 배지 없음. 문구는 설계서 §7-2. */
export const VERDICT_BASIS_BADGE: Record<VerdictBasis, { label: string; description: string } | null> = {
  permit: null,
  proxy: {
    label: "담배소매인 이력 기준",
    description: "편의점 개폐업을 담배소매인 지정·폐업 이력으로 대신 셉니다 — 원천 기준 2026-08",
  },
  aggregate: {
    label: "집계 기반 판정",
    description: "개별 점포의 개업·폐업일이 아니라 서울시 상권분석 동×분기 집계로 판정 — 생존 절벽·조기 폐업은 산출하지 않습니다",
  },
};

/** 판정 제외 업종의 사유 (Task 12 게이트 결과 — 미달 업종만 남긴다). */
const VERDICT_EXCLUSION_REASONS: Record<string, string> = {
  convenience_store: "담배소매인 이력으로 만든 판정이 백테스트 기준(경고 lift 1.10배)을 넘지 못했습니다",
  real_estate: "상권분석 집계로 만든 판정이 백테스트 기준(경고 lift 1.10배)을 넘지 못했습니다",
};

export function verdictExclusionNotice(industryId: string): string {
  return `판정 준비 중인 업종 — ${VERDICT_EXCLUSION_REASONS[industryId] ?? "아직 판정을 제공하지 않습니다"}`;
}

export function isVerdictIndustry(industryId: string): boolean {
  return (INDUSTRIES as readonly string[]).includes(industryId) && !VERDICT_EXCLUDED_INDUSTRIES.has(industryId);
}
