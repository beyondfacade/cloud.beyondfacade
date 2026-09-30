import { expect, it } from "vitest";
import { POST } from "./route";

const url = "http://test/api/mock/admin/auth/password";
const post = (body: unknown, headers: Record<string, string> = { cookie: "metabole_admin=viewer" }) =>
  POST(new Request(url, { method: "POST", headers, body: JSON.stringify(body) }));

it("비로그인은 401", async () => {
  expect((await post({ current_password: "x", new_password: "long-enough-pass" }, {})).status).toBe(401);
});

it("현재 비밀번호가 틀리면 400 WRONG_PASSWORD — 401이 아니다", async () => {
  const res = await post({ current_password: "wrong", new_password: "long-enough-pass" });
  expect(res.status).toBe(400);
  expect((await res.json()).error.code).toBe("WRONG_PASSWORD");
});

it("새 비밀번호가 12자 미만이면 WEAK_PASSWORD, 맞으면 204", async () => {
  expect((await (await post({ current_password: "old-password", new_password: "short" })).json()).error.code).toBe("WEAK_PASSWORD");
  expect((await post({ current_password: "old-password", new_password: "long-enough-pass" })).status).toBe(204);
});
