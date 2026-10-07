import { expect, it } from "vitest";
import { POST } from "./route";

it("모르는 동의 분석 요청은 404 REGION_NOT_FOUND를 반환한다", async () => {
  const response = await POST(new Request("http://test/api/mock/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ region: "unknown_region", industry: "korean_food" }),
  }));
  expect(response.status).toBe(404);
  expect(await response.json()).toEqual({
    error: { code: "REGION_NOT_FOUND", message: "알 수 없는 region_code: unknown_region" },
  });
});

it("모르는 업종의 분석 요청은 404 INDUSTRY_NOT_FOUND를 반환한다", async () => {
  const response = await POST(new Request("http://test/api/mock/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ region: "1168064000", industry: "unknown_industry" }),
  }));
  expect(response.status).toBe(404);
  expect(await response.json()).toEqual({
    error: { code: "INDUSTRY_NOT_FOUND", message: "지원하지 않는 industry: unknown_industry" },
  });
});

it.each([undefined, 0, 50_000_000])("선택 예산 %s가 있는 분석 요청도 분석 ID를 반환한다", async (budget) => {
  const request = new Request("http://test/api/mock/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ region: "1168064000", industry: "korean_food", budget }),
  });
  const response = await POST(request);
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ analysis_id: expect.any(String) });
});

it.each([
  { industry: "korean_food" },
  { region: "1168064000" },
  { region: "", industry: "korean_food" },
  { region: "1168064000", industry: "korean_food", budget: -1 },
  { region: "1168064000", industry: "korean_food", budget: 0.5 },
  { region: "1168064000", industry: "korean_food", budget: "1000" },
  null,
])("필수 값이 없거나 예산이 잘못된 분석 요청은 400 오류를 반환한다: %j", async (body) => {
  const response = await POST(new Request("http://test/api/mock/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }));
  expect(response.status).toBe(400);
  expect(await response.json()).toEqual({
    error: { code: "INVALID_ANALYSIS_REQUEST", message: expect.stringMatching(/[가-힣]/) },
  });
});
