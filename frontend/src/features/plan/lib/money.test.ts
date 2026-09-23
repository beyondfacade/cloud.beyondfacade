import { describe, expect, it } from "vitest";
import { formatManwon, formatPercent, manwonToWon, wonToManwon } from "./money";

describe("원↔만원", () => {
  it("만원으로 반올림한다", () => {
    expect(wonToManwon(31_600_000)).toBe(3160);
    expect(wonToManwon(26_129_731)).toBe(2613);
    expect(manwonToWon(250)).toBe(2_500_000);
  });

  it("표기는 천 단위 구분과 단위를 붙이고 음수 부호를 살린다", () => {
    expect(formatManwon(31_600_000)).toBe("3,160만 원");
    expect(formatManwon(0)).toBe("0만 원");
    expect(formatManwon(-1_680_000)).toBe("−168만 원");
  });

  it("비율은 % 소수 2자리까지", () => {
    expect(formatPercent(0.0405)).toBe("4.05%");
    expect(formatPercent(0.35)).toBe("35%");
  });
});
