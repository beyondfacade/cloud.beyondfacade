import { expect, it } from "vitest";
import { GET } from "./route";

const call = (cookie?: string) =>
  GET(new Request("http://test/api/mock/admin/facility/snapshot", { headers: cookie ? { cookie } : {} }));

it("비로그인은 401", async () => {
  expect((await call()).status).toBe(401);
});

it("호스트·GPU·서비스·DB·수집기 상태를 준다", async () => {
  const body = await (await call("metabole_admin=viewer")).json();
  expect(body.host.cpu_count).toBeGreaterThan(0);
  expect(body.services.map((s: { name: string }) => s.name)).toEqual(["postgres", "ollama"]);
  expect(body.database.alembic_revision).toBeTruthy();
  expect(new Set(body.collectors.map((c: { status: string }) => c.status))).toEqual(new Set(["ok", "late", "missing"]));
});
