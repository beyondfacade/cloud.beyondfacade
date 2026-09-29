import { expect, it } from "vitest";
import { METRIC_SOURCES } from "./metric-sources";

it("지도 원천은 업종별 최신 판정만 제공한다", () => {
  expect(Object.keys(METRIC_SOURCES)).toEqual(["verdict"]);
  expect(METRIC_SOURCES.verdict.axis).toBe("industry_latest");
  expect(METRIC_SOURCES.verdict.queryKey({ industry: "korean_food" })).toEqual(["verdicts", "korean_food"]);
});

it("판정 원천은 네 단계의 순서·색·라벨을 제공한다", () => {
  const source = METRIC_SOURCES.verdict;
  expect(source.order).toEqual(["red", "orange", "clear", "insufficient"]);
  for (const code of source.order) {
    expect(source.palette("light")[code]).toMatch(/^#/);
    expect(source.palette("dark")[code]).toMatch(/^#/);
    expect(source.labelOf(code).name.length).toBeGreaterThan(0);
  }
});
