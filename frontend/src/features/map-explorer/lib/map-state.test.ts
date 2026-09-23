import { expect, it } from "vitest";
import { parseMapState, serializeMapState, SNAPSHOT_INDUSTRIES, YEARS } from "./map-state";

it("YEARS는 2019~2026 8개년을 제공한다 (백엔드 지표 범위와 일치)", () => {
  expect(YEARS).toEqual([2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]);
});

it("기본값: 파라미터 없으면 cafe/closure_rate/2026/null", () => {
  expect(parseMapState(new URLSearchParams())).toEqual({
    industry: "cafe",
    metric: "closure_rate",
    year: 2026,
    region: null,
    budget: null,
  });
});

it("직렬화→파싱 라운드트립이 보존된다", () => {
  const s = {
    industry: "karaoke",
    metric: "growth_rate" as const,
    year: 2021,
    region: "1168051500",
    budget: null,
  };
  expect(parseMapState(new URLSearchParams(serializeMapState(s)))).toEqual(s);
});

it("관문에서 온 budget은 지표를 바꿔도 URL에 남는다 (T3 프리필 원천)", () => {
  const landed = parseMapState(new URLSearchParams("region=1168064000&industry=cafe&budget=50000000"));
  expect(landed.budget).toBe(50_000_000);
  const changed = serializeMapState({ ...landed, metric: "growth_rate" });
  expect(new URLSearchParams(changed).get("budget")).toBe("50000000");
});

it("budget이 숫자가 아니거나 0 이하이면 버린다", () => {
  expect(parseMapState(new URLSearchParams("budget=abc")).budget).toBeNull();
  expect(parseMapState(new URLSearchParams("budget=0")).budget).toBeNull();
});

it("알 수 없는 값은 기본값으로 강제된다", () => {
  expect(parseMapState(new URLSearchParams("industry=hack&metric=x")).industry).toBe("cafe");
});

it("어린이집·편의점도 폐업률·성장률 URL을 그대로 유지한다", () => {
  expect(
    parseMapState(new URLSearchParams("industry=childcare&metric=closure_rate")).metric,
  ).toBe("closure_rate");
  expect(
    parseMapState(new URLSearchParams("industry=convenience_store&metric=growth_rate")).metric,
  ).toBe("growth_rate");
});

it("SNAPSHOT_INDUSTRIES에 어린이집·편의점이 포함된다", () => {
  expect(SNAPSHOT_INDUSTRIES.has("childcare")).toBe(true);
  expect(SNAPSHOT_INDUSTRIES.has("convenience_store")).toBe(true);
});
