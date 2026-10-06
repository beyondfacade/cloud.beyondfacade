import { expect, it } from "vitest";
import { SOURCES } from "./sources";

it("원천 목록이 비어 있지 않고 공공누리 제1유형 원천마다 출처 문구가 있다", () => {
  expect(SOURCES.length).toBeGreaterThan(0);
  const koglSources = SOURCES.filter((source) => source.koglType1);
  expect(koglSources.length).toBeGreaterThan(0);
  expect(koglSources.every((source) => source.attribution?.includes(source.agency))).toBe(true);
});

it("행정동 경계 원천에 SGIS·가공자·이용조건·좌표 축소를 밝힌 출처 문구가 있다", () => {
  expect(SOURCES.find((source) => source.dataset === "행정동 경계(ver20260701)")?.attribution).toBe(
    "본 데이터는 통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr)에서 공공누리 제1유형으로 개방한 행정동 경계를 가공한 것이며(가공: vuski/admdongkor, https://github.com/vuski/admdongkor), CC BY 4.0으로 배포됩니다. 이 서비스는 화면 표시를 위해 좌표를 소수 다섯째 자리로 줄였습니다.",
  );
});
