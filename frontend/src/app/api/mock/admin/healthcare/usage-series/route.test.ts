import { expect, it } from "vitest";
import { GET } from "./route";

const VIEWER = { cookie: "metabole_admin=viewer" };
const get = (query = "", headers: Record<string, string> = VIEWER) =>
  GET(new Request(`http://test/api/mock/admin/healthcare/usage-series${query}`, { headers }));

it("비로그인은 401", async () => {
  expect((await get("", {})).status).toBe(401);
});

it("24시간은 1시간 버킷 24점, 7일은 6시간 버킷 28점이다", async () => {
  const day = await (await get()).json();
  expect([day.hours, day.bucket_hours, day.points.length, day.by_hour.length]).toEqual([24, 1, 24, 24]);
  const week = await (await get("?hours=168")).json();
  expect([week.bucket_hours, week.points.length]).toEqual([6, 28]);
});

it("호출 결과 합계가 요약과 맞는다", async () => {
  const body = await (await get()).json();
  const sum = body.points.reduce((acc: number, p: { ok: number; fallback: number; error: number }) => acc + p.ok + p.fallback + p.error, 0);
  expect(body.outcomes.attempts).toBe(sum);
});

it("허용되지 않은 창은 422", async () => {
  expect((await get("?hours=48")).status).toBe(422);
});
