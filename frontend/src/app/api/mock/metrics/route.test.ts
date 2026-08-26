import { expect, it } from "vitest";
import { GET } from "./route";

it("지원하는 metric은 200과 행 배열을 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026"));
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual(
    expect.arrayContaining([{ region_code: expect.any(String), value: expect.any(Number) }]),
  );
});

it("미지원 metric은 500이 아니라 404 METRIC_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics?metric=unknown_metric"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("METRIC_NOT_FOUND");
});
