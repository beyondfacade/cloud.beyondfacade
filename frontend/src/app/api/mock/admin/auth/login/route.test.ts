import { expect, it } from "vitest";
import { POST } from "./route";

const call = (body: unknown) =>
  POST(new Request("http://test/api/mock/admin/auth/login", { method: "POST", body: JSON.stringify(body) }));

it("로그인하면 httpOnly 세션 쿠키와 등급을 준다 — 토큰은 본문에 없다", async () => {
  const res = await call({ username: "ops", password: "pw" });
  expect(res.status).toBe(200);
  expect(res.headers.get("set-cookie")).toMatch(/metabole_admin=ops; HttpOnly/);
  expect(await res.json()).toEqual({ username: "ops", role: "operator", can_operate: true });
});

it("viewer 계정은 일반 회원이다", async () => {
  const body = await (await call({ username: "viewer", password: "pw" })).json();
  expect(body).toMatchObject({ role: "viewer", can_operate: false });
});

it("이메일로도 로그인한다 — 대소문자 무시", async () => {
  const body = await (await call({ username: "Viewer@Example.com", password: "pw" })).json();
  expect(body).toEqual({ username: "viewer", role: "viewer", can_operate: false });
});

it.each([
  [{ username: "ops", password: "wrong" }],
  [{ username: "nobody", password: "pw" }],
  [{ username: "kim.analyst", password: "pw" }],
])("틀린 비밀번호·없는 계정·구글 전용 정지 계정은 모두 401 INVALID_CREDENTIALS %#", async (body) => {
  const res = await call(body);
  expect(res.status).toBe(401);
  expect((await res.json()).error.code).toBe("INVALID_CREDENTIALS");
});
