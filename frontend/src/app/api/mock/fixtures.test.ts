import { expect, it } from "vitest";
import { SEOUL_REGIONS_GEOJSON, metricRows, summaryOf, agentEventScript } from "./fixtures";

it("geojson feature마다 region_code·name이 있다", () => {
  expect(SEOUL_REGIONS_GEOJSON.features.length).toBeGreaterThanOrEqual(8);
  for (const f of SEOUL_REGIONS_GEOJSON.features)
    expect(f.properties).toMatchObject({ region_code: expect.any(String), name: expect.any(String) });
});
it("metricRows는 모든 feature의 region_code를 커버한다", () => {
  const codes = new Set(metricRows("closure_rate", 2026, "cafe").map((r) => r.region_code));
  for (const f of SEOUL_REGIONS_GEOJSON.features) expect(codes.has(f.properties!.region_code)).toBe(true);
});
it("metricRows는 industry가 다르면 값도 달라진다", () => {
  expect(metricRows("closure_rate", 2026, "cafe")).not.toEqual(metricRows("closure_rate", 2026, "gym"));
});
it("metricRows는 같은 (metric, year, industry)에 대해 결정적이다", () => {
  expect(metricRows("closure_rate", 2026, "cafe")).toEqual(metricRows("closure_rate", 2026, "cafe"));
});
it("summaryOf는 industry가 다르면 점포수·폐업률·성장률 카드 값도 달라진다", () => {
  const code = SEOUL_REGIONS_GEOJSON.features[0].properties!.region_code;
  const cafeCards = summaryOf(code, "cafe").cards.filter((c) => c.grade === "fact");
  const gymCards = summaryOf(code, "gym").cards.filter((c) => c.grade === "fact");
  expect(cafeCards).not.toEqual(gymCards);
});
it("이벤트 스크립트는 report_done으로 끝난다", () => {
  const script = agentEventScript();
  expect(script.at(-1)!.type).toBe("report_done");
});
