import { describe, expect, it } from "vitest";
import { FIRST_QUARTER, LATEST_QUARTER, QUARTERS, formatQuarter, isQuarter, listQuarters } from "./quarters";

describe("분기 어휘", () => {
  it("범위는 백엔드 적재(20211~20262, 22분기)와 같다", () => {
    expect(FIRST_QUARTER).toBe("20211");
    expect(LATEST_QUARTER).toBe("20262");
    expect(QUARTERS).toHaveLength(22);
    expect(QUARTERS[0]).toBe("20211");
    expect(QUARTERS.at(-1)).toBe("20262");
  });

  it("연도 경계를 넘어 오름차순으로 이어진다", () => {
    expect(listQuarters("20213", "20222")).toEqual(["20213", "20214", "20221", "20222"]);
  });

  it("표기는 '2026년 2분기'다", () => {
    expect(formatQuarter("20262")).toBe("2026년 2분기");
    expect(formatQuarter("20211")).toBe("2021년 1분기");
  });

  it("형식이 틀린 분기는 거른다 — URL로 아무 값이나 들어올 수 있다", () => {
    expect(isQuarter("20262")).toBe(true);
    expect(isQuarter("2026")).toBe(false);
    expect(isQuarter("20265")).toBe(false);
    expect(isQuarter(null)).toBe(false);
  });
});
