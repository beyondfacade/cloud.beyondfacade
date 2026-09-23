import { expect, it } from "vitest";
import { GET } from "./route";

function call(query: string) {
  return GET(new Request(`http://test/api/mock/hour-gaps${query}`));
}

it("동×업종은 200과 6구간을 원천 순서로 준다, 분기 생략 시 매출 최신(20254)", async () => {
  const res = await call("?region=1168064000&industry=cafe");
  expect(res.status).toBe(200);
  const gap = await res.json();
  expect(gap.year_quarter).toBe("20254");
  expect(gap.bands.map((b: { hour_band: string }) => b.hour_band)).toEqual(["00_06", "06_11", "11_14", "14_17", "17_21", "21_24"]);
  for (const b of gap.bands) expect(b.gap).toBeCloseTo(b.sales_intensity - b.footfall_intensity, 2);
});

it("강도는 시간당 보정값이라 구간 길이 가중 평균이 1이다", async () => {
  const gap = await (await call("?region=1168064000&industry=cafe")).json();
  const hours = [6, 5, 3, 3, 4, 3];
  const mean = (pick: (b: { footfall_intensity: number; sales_intensity: number }) => number) =>
    gap.bands.reduce((s: number, b: never, i: number) => s + pick(b) * hours[i], 0) / 24;
  expect(mean((b) => b.footfall_intensity)).toBeCloseTo(1, 1);
  expect(mean((b) => b.sales_intensity)).toBeCloseTo(1, 1);
});

it("매출 원천이 없는 업종(어린이집)은 404 HOUR_GAP_NOT_FOUND", async () => {
  const res = await call("?region=1168064000&industry=childcare");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("HOUR_GAP_NOT_FOUND");
});

it("region·industry 누락은 422", async () => {
  expect((await call("?region=1168064000")).status).toBe(422);
});
