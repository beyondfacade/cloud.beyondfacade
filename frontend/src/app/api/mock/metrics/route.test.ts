import { expect, it } from "vitest";
import { GET } from "./route";

it("지원하는 metric·industry는 200과 행 배열을 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual(
    expect.arrayContaining([{ region_code: expect.any(String), value: expect.any(Number) }]),
  );
});

it("미지원 metric은 500이 아니라 404 METRIC_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics?metric=unknown_metric&industry=cafe"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("METRIC_NOT_FOUND");
});

it("지원하지 않는 industry는 404 INDUSTRY_NOT_FOUND를 반환한다", async () => {
  const res = await GET(
    new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=unknown_industry"),
  );
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});

it("업종이 다르면 같은 region·metric이어도 값이 달라진다", async () => {
  const cafeRes = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  const gymRes = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=gym"));
  expect(await cafeRes.json()).not.toEqual(await gymRes.json());
});

it("같은 업종은 같은 (region, industry, metric)에 대해 항상 동일한 값을 반환한다", async () => {
  const first = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  const second = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  expect(await first.json()).toEqual(await second.json());
});
