import { expect, it } from "vitest";
import { parseMapState, serializeMapState, YEARS } from "./map-state";

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

it("알 수 없는 값은 기본값으로 강제된다", () => {
  expect(parseMapState(new URLSearchParams("industry=hack&metric=x"))
    .industry).toBe("cafe");
});
