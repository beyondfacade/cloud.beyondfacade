import { describe, expect, it } from "vitest";
import type { HourGapBand } from "@/shared/api/types";
import { hourGapSentence } from "./hour-gap-sentence";

function band(hour_band: string, footfall: number, sales: number): HourGapBand {
  return { hour_band, footfall_intensity: footfall, sales_intensity: sales, gap: sales - footfall };
}

describe("어긋남 문장", () => {
  it("유동 최대와 매출 최대가 다르면 두 구간을 각각 말한다", () => {
    // 역삼1동×카페 모양 — 유동은 오후가 근소하게 최대, 매출은 점심
    const bands = [band("00_06", 0.3, 0.05), band("06_11", 1.0, 0.7), band("11_14", 1.39, 2.99),
      band("14_17", 1.4, 1.6), band("17_21", 1.1, 1.2), band("21_24", 0.5, 0.35)];
    expect(hourGapSentence(bands)).toBe("사람은 오후(14~17시)에 가장 많고, 돈은 점심(11~14시)에 돕니다.");
  });

  it("두 최대가 같은 구간이면 같이 몰린다고 말한다", () => {
    const bands = [band("06_11", 0.8, 0.6), band("17_21", 1.6, 1.9)];
    expect(hourGapSentence(bands)).toBe("사람과 돈이 저녁(17~21시)에 같이 몰립니다.");
  });

  it("gap의 부호로 판단하지 않는다 — 매출 최대 구간의 gap이 음수여도 그 구간을 말한다", () => {
    // 매출 최대(06_11)가 유동보다 낮아 gap 음수 — 그래도 '돈은 아침에'
    const bands = [band("06_11", 1.5, 1.2), band("11_14", 1.6, 1.1)];
    expect(hourGapSentence(bands)).toBe("사람은 점심(11~14시)에 가장 많고, 돈은 아침(06~11시)에 돕니다.");
  });

  it("행이 없으면 문장도 없다", () => {
    expect(hourGapSentence([])).toBeNull();
  });
});
