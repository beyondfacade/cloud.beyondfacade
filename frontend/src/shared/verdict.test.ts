import { expect, it } from "vitest";
import { SIGNAL_LABELS, VERDICT_CODES, signalLabel, verdictLabel, isVerdictIndustry } from "./verdict";

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

it("신호 5개 라벨", () => {
  expect(Object.keys(SIGNAL_LABELS)).toEqual(["net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking"]);
  expect(signalLabel("net_outflow")).toBe("순유출");
  expect(signalLabel("unknown")).toBe("unknown");
});

it("판정 대상 업종 판별", () => {
  expect(isVerdictIndustry("korean_food")).toBe(true);
  expect(isVerdictIndustry("convenience_store")).toBe(false);
  expect(isVerdictIndustry("academy")).toBe(false);
});

it("폐업 이력이 없는 부동산은 판정 대상에서 제외한다", () => {
  expect(isVerdictIndustry("real_estate")).toBe(false);
});
