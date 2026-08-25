import { expect, it } from "vitest";
import { metricColor } from "./metric-color";

it("sequential: 도메인 하한→상한으로 갈수록 진해진다", () => {
  const lo = metricColor(0, [0, 1], "sequential");
  const hi = metricColor(1, [0, 1], "sequential");
  expect(lo).not.toBe(hi);
  expect(lo).toMatch(/^#[0-9a-f]{6}$/i);
});
it("도메인 밖 값은 경계값으로 클램프된다", () => {
  expect(metricColor(-5, [0, 1], "sequential")).toBe(metricColor(0, [0, 1], "sequential"));
});
it("diverging: 중앙값은 중립색이다", () => {
  const mid = metricColor(0.5, [0, 1], "diverging");
  expect(mid).toMatch(/^#[0-9a-f]{6}$/i);
});
