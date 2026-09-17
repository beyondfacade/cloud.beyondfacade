import { expect, it } from "vitest";
import { GET } from "./route";
import { GET as listCenters } from "../../childcare-centers/route";

it("등록된 region은 200과 마커 목록을 합산한 요약을 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/childcare-center-stats/summary?region=1168064000"));
  expect(res.status).toBe(200);
  const summary = await res.json();
  const centers = await (
    await listCenters(new Request("http://test/api/mock/childcare-centers?region=1168064000"))
  ).json();
  expect(summary).toMatchObject({
    region_code: "1168064000",
    center_count: centers.length,
    capacity: centers.reduce((sum: number, c: { capacity: number }) => sum + c.capacity, 0),
    child_count: centers.reduce((sum: number, c: { child_count: number }) => sum + c.child_count, 0),
  });
  expect(summary.occupancy_rate).toBeCloseTo(summary.child_count / summary.capacity, 4);
});

it("알 수 없는 region은 404 REGION_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/childcare-center-stats/summary?region=9999999999"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("REGION_NOT_FOUND");
});
