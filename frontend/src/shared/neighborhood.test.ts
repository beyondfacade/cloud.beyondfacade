import { describe, expect, it } from "vitest";
import {
  NEIGHBORHOOD_TYPES,
  neighborhoodTypeLabel,
  timeLabelSentence,
} from "./neighborhood";

describe("동네 유형 표기", () => {
  it("여섯 유형 모두 이름·괄호 설명·툴팁을 갖는다", () => {
    expect(NEIGHBORHOOD_TYPES).toHaveLength(6);
    for (const code of NEIGHBORHOOD_TYPES) {
      const label = neighborhoodTypeLabel(code);
      expect(label.name).not.toBe("");
      expect(label.qualifier).not.toBe("");
      expect(label.tooltip).not.toBe("");
    }
  });

  it("혼합형은 이름만으로 뜻이 안 서므로 괄호가 특징 없음을 말한다", () => {
    expect(neighborhoodTypeLabel("mixed").qualifier).toContain("특징 없음");
  });

  it("알 수 없는 코드는 원문을 그대로 이름으로 돌려준다", () => {
    // 백엔드가 유형을 늘려도 화면이 빈 칸으로 깨지지 않는다
    expect(neighborhoodTypeLabel("unknown_type").name).toBe("unknown_type");
  });
});

describe("시간대 서사", () => {
  it("라벨 5종이 각각 한 문장을 갖는다", () => {
    for (const label of ["morning", "day", "evening", "night", "flat"]) {
      expect(timeLabelSentence(label)).toBeTruthy();
    }
  });

  it("라벨이 없으면 문장도 없다", () => {
    expect(timeLabelSentence(null)).toBeNull();
  });
});
