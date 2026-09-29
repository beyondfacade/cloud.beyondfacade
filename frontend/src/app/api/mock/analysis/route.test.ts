import { expect, it } from "vitest";
import { POST } from "./route";

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
