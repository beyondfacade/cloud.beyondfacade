import { expect, it } from "vitest";
import { GET } from "./route";
import { GET as listStores } from "../route";

it("등록된 region은 200과 마커 목록의 브랜드별 집계를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/convenience-stores/summary?region=1168064000"));
  expect(res.status).toBe(200);
  const summary = await res.json();
  const stores: { brand: string | null }[] = await (
    await listStores(new Request("http://test/api/mock/convenience-stores?region=1168064000"))
  ).json();
  expect(summary.region_code).toBe("1168064000");
  expect(summary.store_count).toBe(stores.length);
  const total = summary.brands.reduce((sum: number, b: { count: number }) => sum + b.count, 0);
  expect(total).toBe(stores.length);
  // 미확인(null) 브랜드는 항상 맨 뒤 — 실 API 정렬 규칙과 동일
  const nullIndex = summary.brands.findIndex((b: { brand: string | null }) => b.brand === null);
  expect(nullIndex === -1 || nullIndex === summary.brands.length - 1).toBe(true);
});

it("알 수 없는 region은 404 REGION_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/convenience-stores/summary?region=9999999999"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("REGION_NOT_FOUND");
});
