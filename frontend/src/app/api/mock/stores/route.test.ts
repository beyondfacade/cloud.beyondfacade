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

// 표본상 cafe는 전 지역 status_name이 "영업"뿐이라(폐업 표본 없음) closed 검증엔 billiard를 쓴다(region 1168052100엔 폐업 표본 有).
it("status=closed는 폐업 점포만 close_date와 함께 주고, 기본값은 close_date가 null이다", async () => {
  const closed = await (await GET(new Request("http://test/api/mock/stores?region=1168052100&industry=billiard&status=closed"))).json();
  expect(closed.length).toBeGreaterThan(0);
  for (const s of closed) {
    expect(s.status_name).toBe("폐업");
    expect(s.close_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  }
  const open = await (await GET(new Request("http://test/api/mock/stores?region=1168052100&industry=billiard"))).json();
  for (const s of open) expect(s.close_date).toBeNull();
});

it("미지원 status는 404 STORE_STATUS_NOT_FOUND", async () => {
  const res = await GET(new Request("http://test/api/mock/stores?region=1168052100&industry=cafe&status=bogus"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("STORE_STATUS_NOT_FOUND");
});
