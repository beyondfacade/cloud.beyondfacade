import { describe, expect, it } from "vitest";
import { NEIGHBORHOOD_TYPES } from "@/shared/neighborhood";
import { NEIGHBORHOOD_PALETTES, neighborhoodPalette, relativeLuminance } from "./neighborhood-palette";

const HEX = /^#[0-9a-f]{6}$/i;

describe("동네 유형 팔레트", () => {
  it.each(["light", "dark"] as const)("%s — 6종 전부 hex이고 서로 다르다", (theme) => {
    const palette = neighborhoodPalette(theme);
    const colors = NEIGHBORHOOD_TYPES.map((type) => palette[type]);
    expect(colors).toHaveLength(6);
    for (const color of colors) expect(color).toMatch(HEX);
    expect(new Set(colors.map((c) => c.toLowerCase())).size).toBe(6);
  });

  it("라이트 — 주거형이 가장 밝다 (배경에 가장 가깝게, 60%가 지도를 지배하지 않도록)", () => {
    const palette = NEIGHBORHOOD_PALETTES.light;
    const others = NEIGHBORHOOD_TYPES.filter((t) => t !== "residential");
    for (const type of others) {
      expect(relativeLuminance(palette.residential)).toBeGreaterThan(relativeLuminance(palette[type]));
    }
  });

  it("다크 — 주거형이 가장 어둡다 (밤 타일에 가장 가깝게)", () => {
    const palette = NEIGHBORHOOD_PALETTES.dark;
    const others = NEIGHBORHOOD_TYPES.filter((t) => t !== "residential");
    for (const type of others) {
      expect(relativeLuminance(palette.residential)).toBeLessThan(relativeLuminance(palette[type]));
    }
  });

  it("relativeLuminance — 검정 0, 흰색 1", () => {
    expect(relativeLuminance("#000000")).toBe(0);
    expect(relativeLuminance("#ffffff")).toBeCloseTo(1, 5);
  });
});
