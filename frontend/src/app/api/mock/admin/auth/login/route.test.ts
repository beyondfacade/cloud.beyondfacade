import { expect, it } from "vitest";
import { POST } from "./route";

const call = (body: unknown) =>
  POST(new Request("http://test/api/mock/admin/auth/login", { method: "POST", body: JSON.stringify(body) }));

it("로그인하면 httpOnly 세션 쿠키와 역할을 준다 — 토큰은 본문에 없다", async () => {
  const res = await call({ username: "ops", password: "pw" });
  expect(res.status).toBe(200);
  expect(res.headers.get("set-cookie")).toMatch(/metabole_admin=operator; HttpOnly/);
  expect(await res.json()).toEqual({ username: "ops", role: "operator", can_operate: true });
});

it("viewer 계정은 조회 관리자다", async () => {
  const body = await (await call({ username: "viewer", password: "pw" })).json();
  expect(body).toMatchObject({ role: "viewer", can_operate: false });
});

it("틀린 비밀번호는 401 INVALID_CREDENTIALS", async () => {
  const res = await call({ username: "ops", password: "wrong" });
  expect(res.status).toBe(401);
  expect((await res.json()).error.code).toBe("INVALID_CREDENTIALS");
});
