import { expect, it } from "vitest";
import { makeCategoryColorScale, NO_DATA_COLOR } from "./metric-color";

const PALETTE = { office: "#111111", residential: "#eeeeee", mixed: "#888888" };
const ORDER = ["office", "residential", "mixed"] as const;

it("범주 스케일: colorOf와 classes가 같은 팔레트를 본다 — 지도 색과 범례 색이 어긋나지 않는다", () => {
  const { colorOf, classes } = makeCategoryColorScale(["residential", "office"], PALETTE, ORDER);
  expect(colorOf("office")).toBe("#111111");
  expect(classes.find((c) => c.code === "office")?.color).toBe(colorOf("office"));
});

it("범주 스케일: classes는 order 순 전체 키다 — 데이터에 없는 유형도 범례에 보인다", () => {
  const { classes } = makeCategoryColorScale(["residential"], PALETTE, ORDER);
  expect(classes.map((c) => c.code)).toEqual([...ORDER]);
});

it("범주 스케일: 모르는 코드는 NO_DATA_COLOR, 코드가 없으면 빈 classes", () => {
  expect(makeCategoryColorScale(["office"], PALETTE, ORDER).colorOf("brand_new")).toBe(NO_DATA_COLOR);
  expect(makeCategoryColorScale([], PALETTE, ORDER).classes).toEqual([]);
});
