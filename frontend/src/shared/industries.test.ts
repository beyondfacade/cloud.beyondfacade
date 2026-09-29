import { expect, it } from "vitest";
import { INDUSTRIES, INDUSTRY_GROUPS, INDUSTRY_LABELS, industryLabel, isKnownIndustry } from "./industries";

it("업종 select는 14종이고 음식 6종이 들어 있다 (HANDOFF §0-9)", () => {
  expect(INDUSTRIES).toHaveLength(14);
  for (const id of ["korean_food", "chinese_food", "japanese_food", "western_food", "snack", "pub"]) {
    expect(INDUSTRIES, id).toContain(id);
  }
});

it("학원·어린이집은 라벨은 있지만 판정 대상(select) 목록에는 없다 (HANDOFF §0-11 보조축)", () => {
  expect(INDUSTRY_LABELS.academy).toBe("학원");
  expect(INDUSTRY_LABELS.childcare).toBe("어린이집");
  expect(INDUSTRIES).not.toContain("academy");
  expect(INDUSTRIES).not.toContain("childcare");
});

it("비노출 restaurant_other는 라벨에도 없다 — 관문·select 어디서도 고를 수 없다", () => {
  expect(isKnownIndustry("restaurant_other")).toBe(false);
});

it("optgroup 3개(음식·생활·여가)의 합이 곧 판정 대상 목록이고 중복이 없다", () => {
  expect(INDUSTRY_GROUPS.map((g) => g.label)).toEqual(["음식", "생활", "여가"]);
  const flat = INDUSTRY_GROUPS.flatMap((g) => [...g.ids]);
  expect(flat).toEqual([...INDUSTRIES]);
  expect(new Set(flat).size).toBe(flat.length);
});

it("라벨 조회는 마스터 업종이면 라벨, 아니면 원문을 돌려준다", () => {
  expect(industryLabel("korean_food")).toBe("한식");
  expect(industryLabel("academy")).toBe("학원");
  expect(industryLabel("unknown")).toBe("unknown");
});
