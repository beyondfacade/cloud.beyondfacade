import { expect, it } from "vitest";
import { GET } from "./route";

it("등록된 region은 200과 편의점 마커 배열을 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/convenience-stores?region=1168064000"));
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.length).toBeGreaterThan(0);
  expect(body[0]).toMatchObject({
    store_id: expect.any(String),
    name: expect.any(String),
    lat: expect.any(Number),
    lng: expect.any(Number),
  });
  expect(body[0]).toHaveProperty("brand");
  expect(body[0]).toHaveProperty("branch_name");
  expect(body[0]).toHaveProperty("road_address");
});

it("같은 region은 항상 같은 목록을 반환한다 (결정적 픽스처)", async () => {
  const url = "http://test/api/mock/convenience-stores?region=1168064000";
  expect(await (await GET(new Request(url))).json()).toEqual(await (await GET(new Request(url))).json());
});

it("알 수 없는 region은 404 REGION_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/convenience-stores?region=9999999999"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("REGION_NOT_FOUND");
});
