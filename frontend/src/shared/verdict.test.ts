import { expect, it } from "vitest";
import { ADVISORY_SIGNAL_KEYS, SIGNAL_LABELS, VERDICT_BASIS_BADGE, VERDICT_CODES, signalLabel, verdictLabel, isVerdictIndustry, verdictExclusionNotice } from "./verdict";

it("판정 코드 순서는 빨강→주황→경고 없음→보류다 (범례 순서)", () => {
  expect(VERDICT_CODES).toEqual(["red", "orange", "clear", "insufficient"]);
});

it("판정 라벨은 이름과 괄호 설명을 갖고, 🟢 추천은 없다", () => {
  expect(verdictLabel("red")).toEqual({ name: "비추천", qualifier: "강한 경고 신호 2개 이상" });
  expect(verdictLabel("orange").name).toBe("조건부");
  expect(verdictLabel("clear").name).toBe("경고 없음");
  expect(verdictLabel("insufficient")).toEqual({ name: "판정 보류", qualifier: "표본 부족 — 판정 가능한 신호 2개 미만" });
  expect(Object.values(VERDICT_CODES)).not.toContain("green");
});

it("알 수 없는 코드는 원문을 이름으로 돌려준다", () => {
  expect(verdictLabel("weird").name).toBe("weird");
});

it("신호 라벨은 공통 4개 뒤에 업종 특화 신호를 둔다", () => {
  expect(Object.keys(SIGNAL_LABELS)).toEqual(["net_outflow", "survival_cliff", "early_closure", "saturation", "closure_rate", "tobacco_gap", "trade_per_office"]);
  expect(signalLabel("net_outflow")).toBe("순유출");
  expect(signalLabel("closure_rate")).toBe("폐업률");
  expect(signalLabel("tobacco_gap")).toBe("담배권 빈자리");
  expect(signalLabel("trade_per_office")).toBe("사무소당 거래");
  expect(signalLabel("unknown")).toBe("unknown");
});

it("담배권 빈자리와 사무소당 거래는 참고 신호다", () => {
  expect(ADVISORY_SIGNAL_KEYS.has("tobacco_gap")).toBe(true);
  expect(ADVISORY_SIGNAL_KEYS.has("trade_per_office")).toBe(true);
});

it("판정 원천 배지는 인허가에는 없고 대리·집계 원천에만 있다", () => {
  expect(VERDICT_BASIS_BADGE.permit).toBeNull();
  expect(VERDICT_BASIS_BADGE.proxy?.label).toBe("담배소매인 이력 기준");
  expect(VERDICT_BASIS_BADGE.aggregate?.label).toBe("집계 기반 판정");
});

it("판정 제외 업종 안내 문구는 업종별 사유를 붙이고 모르는 업종은 기본 문구다", () => {
  expect(verdictExclusionNotice("academy")).toBe("판정 준비 중인 업종 — 아직 판정을 제공하지 않습니다");
});

it("판정 대상 업종 판별", () => {
  expect(isVerdictIndustry("korean_food")).toBe(true);
  expect(isVerdictIndustry("academy")).toBe(false);
});

it("담배소매인 이력 판정이 게이트를 넘지 못해 편의점은 여전히 판정 대상이 아니다", () => {
  expect(isVerdictIndustry("convenience_store")).toBe(false);
  expect(verdictExclusionNotice("convenience_store")).toBe(
    "판정 준비 중인 업종 — 담배소매인 이력으로 만든 판정이 백테스트 기준(경고 lift 1.10배)을 넘지 못했습니다",
  );
});

it("상권분석 집계 판정이 게이트를 넘지 못해 부동산은 여전히 판정 대상이 아니다", () => {
  expect(isVerdictIndustry("real_estate")).toBe(false);
  expect(verdictExclusionNotice("real_estate")).toBe(
    "판정 준비 중인 업종 — 상권분석 집계로 만든 판정이 백테스트 기준(경고 lift 1.10배)을 넘지 못했습니다",
  );
});
