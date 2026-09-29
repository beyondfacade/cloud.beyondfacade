import { expect, it } from "vitest";
import { verdictPalette } from "./verdict-palette";

/** WCAG 상대 명도 — 판정 팔레트 대비를 검증하는 테스트 도우미. */
function relativeLuminance(hex: string): number {
  const channel = (index: number) => {
    const c = parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2);
}

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
