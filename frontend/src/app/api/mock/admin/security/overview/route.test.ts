import { expect, it } from "vitest";
import { GET } from "./route";

const call = (cookie?: string) =>
  GET(new Request("http://test/api/mock/admin/security/overview", { headers: cookie ? { cookie } : {} }));

it("비로그인은 401", async () => {
  expect((await call()).status).toBe(401);
});

it("요약·알림·최근 이벤트를 주고 알림은 심각도 순이다", async () => {
  const body = await (await call("metabole_admin=viewer")).json();
  expect(body.summary.open_alerts).toBe(body.alerts.length);
  expect(body.alerts.map((a: { severity: string }) => a.severity)).toEqual(["critical", "medium"]);
  expect(body.recent_events.length).toBeGreaterThan(0);
});
