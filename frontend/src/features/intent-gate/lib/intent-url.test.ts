import { expect, it } from "vitest";
import { intentToUrl, planUrl } from "./intent-url";

it("동·업종·예산을 전부 실어 지도로 보낸다", () => {
  expect(intentToUrl({ region_code: "1168064000", industry_id: "cafe", budget_krw: 50_000_000 }))
    .toBe("/map?region=1168064000&industry=cafe&budget=50000000");
});

it("없는 값은 생략한다 (B유형은 region만, C유형은 industry만)", () => {
  expect(intentToUrl({ region_code: "1144071000", industry_id: null, budget_krw: null })).toBe("/map?region=1144071000");
  expect(intentToUrl({ region_code: null, industry_id: "karaoke", budget_krw: null })).toBe("/map?industry=karaoke");
});

it("아무것도 없으면 지도 기본 경로다", () => {
  expect(intentToUrl({ region_code: null, industry_id: null, budget_krw: null })).toBe("/map");
});

it("planUrl: 동과 업종이 다 있을 때만, 예산을 실어서", () => {
  expect(planUrl({ region_code: "1168064000", industry_id: "cafe", budget_krw: 50000000 })).toBe("/plan?region=1168064000&industry=cafe&budget=50000000");
  expect(planUrl({ region_code: "1168064000", industry_id: "cafe", budget_krw: null })).toBe("/plan?region=1168064000&industry=cafe");
  expect(planUrl({ region_code: "1168064000", industry_id: null, budget_krw: null })).toBeNull();
});
