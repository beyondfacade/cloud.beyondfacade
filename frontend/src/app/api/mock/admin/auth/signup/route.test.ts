import { expect, it } from "vitest";
import { GET } from "../me/route";
import { POST } from "./route";

const call = (body: Record<string, unknown>) =>
  POST(new Request("http://test/api/mock/admin/auth/signup", {
    method: "POST",
    body: JSON.stringify({ username: "new.one", email: "new@example.com", password: "long-enough-pw", ...body }),
  }));

it("가입하면 201과 httpOnly 세션 쿠키, 일반 등급을 준다", async () => {
  const res = await call({});
  expect(res.status).toBe(201);
  expect(res.headers.get("set-cookie")).toMatch(/metabole_admin=new\.one; HttpOnly/);
  expect(await res.json()).toEqual({ username: "new.one", role: "viewer", can_operate: false });
  const me = await GET(new Request("http://test/api/mock/admin/auth/me", { headers: { cookie: "metabole_admin=new.one" } }));
  expect(await me.json()).toEqual({ username: "new.one", role: "viewer", can_operate: false });
});

it.each([
  [{ username: "ops" }, 409, "USERNAME_TAKEN"],
  [{ username: "Bad Name" }, 400, "INVALID_USERNAME"],
  [{ username: "fresh", email: "nope" }, 400, "INVALID_EMAIL"],
  [{ username: "fresh", password: "short" }, 400, "WEAK_PASSWORD"],
  [{ username: "fresh", email: "VIEWER@example.com" }, 409, "EMAIL_TAKEN"],
])("규칙 위반은 실 API와 같은 코드로 거절한다 %#", async (body, status, code) => {
  const res = await call(body);
  expect(res.status).toBe(status);
  expect((await res.json()).error.code).toBe(code);
});
