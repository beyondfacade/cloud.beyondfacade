import { expect, it } from "vitest";
import { GET } from "./route";

it("등록된 region·industry는 200과 점포 배열을 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/stores?region=1168064000&industry=cafe"));
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.length).toBeGreaterThan(0);
  expect(body[0]).toMatchObject({
    store_id: expect.any(String),
    name: expect.any(String),
    lat: expect.any(Number),
    lng: expect.any(Number),
    status_name: expect.any(String),
    open_date: expect.any(String),
  });
});

it("알 수 없는 region은 404 REGION_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/stores?region=9999999999&industry=cafe"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("REGION_NOT_FOUND");
});

it("지원하지 않는 industry는 404 INDUSTRY_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/stores?region=1168064000&industry=unknown_industry"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});

it("실적재 데이터가 없는 업종은 (region·industry 모두 유효해도) 빈 배열을 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/stores?region=1168064000&industry=convenience_store"));
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual([]);
});
