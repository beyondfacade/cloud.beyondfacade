import { expect, it } from "vitest";
import { GET } from "./route";

const VIEWER = { cookie: "metabole_admin=viewer" };
const get = (query = "", headers: Record<string, string> = VIEWER) =>
  GET(new Request(`http://test/api/mock/admin/facility/history${query}`, { headers }));

it("비로그인은 401", async () => {
  expect((await get("", {})).status).toBe(401);
});

it("24시간 추세는 6분 버킷, 7일은 42분 버킷이고 점은 240개 이하다", async () => {
  const day = await (await get()).json();
  expect(day.bucket_seconds).toBe(360);
  expect(day.points.length).toBeLessThanOrEqual(240);
  expect(day.points[0]).toHaveProperty("cpu_percent");
  const week = await (await get("?hours=168")).json();
  expect(week.bucket_seconds).toBe(2520);
});

it("점은 오래된 것부터다", async () => {
  const { points } = await (await get("?hours=1")).json();
  expect(Date.parse(points[0].t)).toBeLessThan(Date.parse(points[points.length - 1].t));
});

it("허용되지 않은 창은 422", async () => {
  expect((await get("?hours=5")).status).toBe(422);
});
