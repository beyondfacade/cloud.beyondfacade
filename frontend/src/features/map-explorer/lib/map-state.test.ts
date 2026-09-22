import { expect, it } from "vitest";
import { metricsForIndustry, parseMapState, serializeMapState, YEARS } from "./map-state";

it("YEARS는 2019~2026 8개년을 제공한다 (백엔드 지표 범위와 일치)", () => {
  expect(YEARS).toEqual([2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]);
});

it("기본값: 파라미터 없으면 cafe/closure_rate/2026/null", () => {
  expect(parseMapState(new URLSearchParams())).toEqual({
    industry: "cafe",
    metric: "closure_rate",
    year: 2026,
    region: null,
  });
});

it("직렬화→파싱 라운드트립이 보존된다", () => {
  const s = {
    industry: "karaoke",
    metric: "growth_rate" as const,
    year: 2021,
    region: "1168051500",
  };
  expect(parseMapState(new URLSearchParams(serializeMapState(s)))).toEqual(s);
});

it("어린이집·편의점은 폐업률 URL이어도 점포수로 보정한다", () => {
  expect(
    parseMapState(new URLSearchParams("industry=childcare&metric=closure_rate")).metric,
  ).toBe("store_count");
  expect(
    parseMapState(new URLSearchParams("industry=convenience_store&metric=growth_rate")).metric,
  ).toBe("store_count");
});

it("metricsForIndustry는 스냅샷 업종에 점포수만 반환한다", () => {
  expect(metricsForIndustry("childcare")).toEqual(["store_count"]);
  expect(metricsForIndustry("cafe")).toEqual(["closure_rate", "growth_rate", "store_count"]);
});
