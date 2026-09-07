import { expect, it } from "vitest";
import { makeMetricColorScale, NO_DATA_COLOR } from "./metric-color";

const HEX = /^#[0-9a-f]{6}$/i;

it("sequential: 분위수 클래스 — 값이 클수록 진한 클래스, 낮은 값과 다른 색", () => {
  const values = Array.from({ length: 100 }, (_, i) => i);
  const { colorOf } = makeMetricColorScale(values, "sequential");
  expect(colorOf(0)).toMatch(HEX);
  expect(colorOf(0)).not.toBe(colorOf(99));
});

it("sequential: 분위수 기준 — 고른 분포면 7개 클래스가 전부 쓰인다", () => {
  const values = Array.from({ length: 700 }, (_, i) => i);
  const { colorOf } = makeMetricColorScale(values, "sequential");
  const used = new Set(values.map(colorOf));
  expect(used.size).toBe(7);
});

it("sequential: 도메인 밖 값은 경계 클래스로 클램프된다", () => {
  const values = [10, 20, 30, 40, 50];
  const { colorOf } = makeMetricColorScale(values, "sequential");
  expect(colorOf(-999)).toBe(colorOf(10));
  expect(colorOf(999)).toBe(colorOf(50));
});

it("diverging: 0은 중립색, 음수는 파랑 계열, 양수는 빨강 계열", () => {
  const { colorOf } = makeMetricColorScale([-0.08, -0.02, 0, 0.03, 0.12], "diverging");
  expect(colorOf(0)).toBe("#f7f7f7");
  expect(colorOf(-0.12)).toBe("#2166ac"); // 최저 = 가장 진한 파랑
  expect(colorOf(0.12)).toBe("#b2182b"); // 최고 = 가장 진한 빨강
});

it("diverging: 0 중심 대칭 — 데이터가 양수로 치우쳐도 음수는 파랑을 유지한다", () => {
  const { colorOf } = makeMetricColorScale([-0.04, 0.05, 0.1, 0.12], "diverging");
  expect(["#2166ac", "#4393c3", "#92c5de"]).toContain(colorOf(-0.04));
});

it("값이 비어 있으면 NO_DATA_COLOR와 빈 classes를 반환한다", () => {
  const { colorOf, classes } = makeMetricColorScale([], "sequential");
  expect(colorOf(5)).toBe(NO_DATA_COLOR);
  expect(classes).toEqual([]);
});

it("classes: 7개 구간이 최솟값~최댓값을 빈틈없이 잇는다", () => {
  const values = Array.from({ length: 100 }, (_, i) => i);
  const { classes } = makeMetricColorScale(values, "sequential");
  expect(classes).toHaveLength(7);
  expect(classes[0].from).toBe(0);
  expect(classes[6].to).toBe(99);
  for (let i = 0; i < 6; i++) expect(classes[i].to).toBe(classes[i + 1].from);
});

it("classes(sequential): 경계가 분위수 값과 일치한다 — colorOf와 단일 원천", () => {
  const values = Array.from({ length: 100 }, (_, i) => i); // 균등 분포 → p분위수 = p*99
  const { colorOf, classes } = makeMetricColorScale(values, "sequential");
  expect(classes[0].to).toBeCloseTo(99 / 7, 5);
  expect(classes[3].to).toBeCloseTo((4 * 99) / 7, 5);
  // 구간 하한의 색 = 그 구간의 색 (경계 포함 방향 [from, to) 일관성)
  expect(colorOf(classes[3].from)).toBe(classes[3].color);
});

it("classes(diverging): 0 중심 대칭 — 양끝은 ±extent, 중앙 구간이 0을 포함한다", () => {
  const { classes } = makeMetricColorScale([-0.04, 0.05, 0.1, 0.12], "diverging");
  expect(classes[0].from).toBeCloseTo(-0.12, 10);
  expect(classes[6].to).toBeCloseTo(0.12, 10);
  expect(classes[0].from).toBeCloseTo(-classes[6].to, 10);
  expect(classes[3].color).toBe("#f7f7f7");
  expect(classes[3].from).toBeLessThan(0);
  expect(classes[3].to).toBeGreaterThan(0);
});
