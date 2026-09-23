import { expect, it } from "vitest";
import { METRICS, METRIC_GROUPS, metricGroupOf, parseMapState, serializeMapState, SNAPSHOT_INDUSTRIES, YEARS } from "./map-state";

it("YEARS는 2019~2026 8개년을 제공한다 (백엔드 지표 범위와 일치)", () => {
  expect(YEARS).toEqual([2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]);
});

it("기본값: 파라미터 없으면 cafe/neighborhood_type/2026/null — 첫 질문은 '어디가 어떤 곳이냐'다", () => {
  expect(parseMapState(new URLSearchParams())).toEqual({
    industry: "cafe",
    metric: "neighborhood_type",
    year: 2026,
    year_quarter: null,
    region: null,
    budget: null,
  });
});

it("직렬화→파싱 라운드트립이 보존된다", () => {
  const s = {
    industry: "karaoke",
    metric: "growth_rate" as const,
    year: 2021,
    year_quarter: null,
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
  const parsed = parseMapState(new URLSearchParams("industry=hack&metric=x"));
  expect(parsed.industry).toBe("cafe");
  expect(parsed.metric).toBe("neighborhood_type");
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

it("지표는 두 무리에서 파생되고 무리 밖 지표가 없다", () => {
  expect(METRIC_GROUPS.map((g) => g.key)).toEqual(["region", "industry"]);
  const fromGroups = METRIC_GROUPS.flatMap((g) => [...g.metrics]);
  expect([...METRICS]).toEqual(fromGroups);
  for (const m of METRICS) expect(metricGroupOf(m).metrics).toContain(m);
  expect(metricGroupOf("night_index").axis).toBe("region_quarter");
  expect(metricGroupOf("closure_rate").axis).toBe("industry_year");
});

it("year_quarter는 URL을 왕복하고, 형식이 틀리면 null(최신)이다", () => {
  const s = { ...parseMapState(new URLSearchParams()), metric: "night_index" as const, year_quarter: "20254" };
  const round = parseMapState(new URLSearchParams(serializeMapState(s)));
  expect(round.year_quarter).toBe("20254");
  expect(parseMapState(new URLSearchParams("year_quarter=2025")).year_quarter).toBeNull();
  // null이면 URL에 안 실린다 — 최신은 백엔드가 고른다
  expect(new URLSearchParams(serializeMapState({ ...s, year_quarter: null })).has("year_quarter")).toBe(false);
});

it("무리를 오가도 연도·분기·예산이 각자 유지된다", () => {
  const landed = parseMapState(new URLSearchParams("region=1168064000&industry=cafe&budget=50000000&year=2023&year_quarter=20244"));
  const toIndustry = parseMapState(new URLSearchParams(serializeMapState({ ...landed, metric: "closure_rate" })));
  const backToRegion = parseMapState(new URLSearchParams(serializeMapState({ ...toIndustry, metric: "fnb_share" })));
  expect(backToRegion).toMatchObject({ year: 2023, year_quarter: "20244", budget: 50_000_000, industry: "cafe" });
});
