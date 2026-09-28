import { expect, it } from "vitest";
import { relativeLuminance } from "./neighborhood-palette";
import { verdictPalette } from "./verdict-palette";

it("라이트·다크 둘 다 4범주 색을 갖는다", () => {
  for (const theme of ["light", "dark"] as const) {
    expect(Object.keys(verdictPalette(theme)).sort()).toEqual(["clear", "insufficient", "orange", "red"]);
  }
});

it("경고 없음·보류가 가장 옅다 — 빨강·주황이 지도에서 튀어야 한다", () => {
  const light = verdictPalette("light");
  expect(relativeLuminance(light.clear)).toBeGreaterThan(relativeLuminance(light.red));
  expect(relativeLuminance(light.clear)).toBeGreaterThan(relativeLuminance(light.orange));
  const dark = verdictPalette("dark");
  expect(relativeLuminance(dark.clear)).toBeLessThan(relativeLuminance(dark.red));
});
