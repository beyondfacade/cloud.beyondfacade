import { expect, it } from "vitest";
import { SEOUL_SAMPLE_GEOJSON, metricRows, agentEventScript } from "./fixtures";

it("geojson feature마다 region_code·name이 있다", () => {
  expect(SEOUL_SAMPLE_GEOJSON.features.length).toBeGreaterThanOrEqual(8);
  for (const f of SEOUL_SAMPLE_GEOJSON.features)
    expect(f.properties).toMatchObject({ region_code: expect.any(String), name: expect.any(String) });
});
it("metricRows는 모든 feature의 region_code를 커버한다", () => {
  const codes = new Set(metricRows("closure_rate", 2026).map((r) => r.region_code));
  for (const f of SEOUL_SAMPLE_GEOJSON.features) expect(codes.has(f.properties!.region_code)).toBe(true);
});
it("이벤트 스크립트는 report_done으로 끝난다", () => {
  const script = agentEventScript();
  expect(script.at(-1)!.type).toBe("report_done");
});
