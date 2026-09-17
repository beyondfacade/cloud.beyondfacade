import { expect, it } from "vitest";
import { formatOccupancy, formatWaiting } from "./childcare-format";

it("formatOccupancy: 비율을 소수 1자리 %로, 정원 없음(null)은 대시로 표시한다", () => {
  expect(formatOccupancy(0.6205)).toBe("62.1%");
  expect(formatOccupancy(1)).toBe("100.0%");
  expect(formatOccupancy(null)).toBe("—");
});

it("formatWaiting: 건수는 천 단위 구분, 원천 공란(null)은 미공개로 표시한다", () => {
  expect(formatWaiting(1034)).toBe("1,034건");
  expect(formatWaiting(0)).toBe("0건");
  expect(formatWaiting(null)).toBe("미공개");
});
