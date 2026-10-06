import { expect, it } from "vitest";
import { SOURCES } from "./sources";

it("원천 목록이 비어 있지 않고 공공누리 제1유형 원천마다 출처 문구가 있다", () => {
  expect(SOURCES.length).toBeGreaterThan(0);
  const koglSources = SOURCES.filter((source) => source.koglType1);
  expect(koglSources.length).toBeGreaterThan(0);
  expect(koglSources.every((source) => source.attribution?.includes(source.agency))).toBe(true);
});
