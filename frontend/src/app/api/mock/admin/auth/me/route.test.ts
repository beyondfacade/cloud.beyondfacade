import { expect, it } from "vitest";
import { GET } from "./route";

const call = (cookie?: string) =>
  GET(new Request("http://test/api/mock/admin/auth/me", { headers: cookie ? { cookie } : {} }));

it("세션 쿠키가 없으면 401 UNAUTHENTICATED", async () => {
  const res = await call();
  expect(res.status).toBe(401);
  expect((await res.json()).error.code).toBe("UNAUTHENTICATED");
});

it("세션 쿠키의 역할을 돌려준다", async () => {
  const body = await (await call("theme=dark; metabole_admin=viewer")).json();
  expect(body).toEqual({ username: "viewer", role: "viewer", can_operate: false });
});
