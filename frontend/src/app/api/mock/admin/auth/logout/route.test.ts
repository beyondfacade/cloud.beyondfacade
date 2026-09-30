import { expect, it } from "vitest";
import { POST } from "./route";

it("로그아웃은 204와 함께 세션 쿠키를 지운다", async () => {
  const res = await POST();
  expect(res.status).toBe(204);
  expect(res.headers.get("set-cookie")).toMatch(/metabole_admin=;.*Max-Age=0/);
});
