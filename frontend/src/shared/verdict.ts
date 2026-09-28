/** 판정 코드·신호 키의 표기 어휘. 코드는 API 계약 값이라 영문 유지, 화면엔 라벨만.
 *  판정은 백엔드 verdict 배치가 하고 여기는 사람이 읽는 말로 옮기기만 한다. 🟢 추천은 없다(HANDOFF §0-2).
 *  지도 범례·사이드패널 카드가 함께 쓰므로 shared에 둔다. */
import type { VerdictCode, VerdictSignalKey } from "@/shared/api/types";
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
  insufficient: { name: "판정 보류", qualifier: "표본 부족 — 판정 가능한 신호 3개 미만" },
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
};

export function signalLabel(key: string): string {
  return SIGNAL_LABELS[key as VerdictSignalKey] ?? key;
}

/** 판정 대상에서 빠진 select 업종 — 편의점은 스냅샷 전용 원천이라 백엔드 verdict가 없다(1단계 Ruling A, 특화 신호 단계까지).
 *  백엔드 `EXCLUDED_INDUSTRIES` 중 프론트 `INDUSTRIES`(14)에 남아 있는 것만 여기 둔다. */
export const VERDICT_EXCLUDED_INDUSTRIES: ReadonlySet<string> = new Set(["convenience_store"]);

export function isVerdictIndustry(industryId: string): boolean {
  return (INDUSTRIES as readonly string[]).includes(industryId) && !VERDICT_EXCLUDED_INDUSTRIES.has(industryId);
}
