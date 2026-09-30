import { expect, it } from "vitest";
import { PATCH } from "./route";
import { auditEntries } from "../../security/audit/store";
import { accounts } from "../../users/store";

const url = "http://test/api/mock/admin/auth/username";
const patch = (username: unknown, cookie?: string) =>
  PATCH(new Request(url, {
    method: "PATCH",
    headers: { "content-type": "application/json", ...(cookie ? { cookie: `metabole_admin=${cookie}` } : {}) },
    body: JSON.stringify({ username }),
  }));

it("비로그인은 401", async () => {
  expect((await patch("anyone")).status).toBe(401);
});

it.each([
  ["ops", 409, "USERNAME_TAKEN"],
  ["Bad Name", 400, "INVALID_USERNAME"],
  ["ab", 400, "INVALID_USERNAME"],
])("%s(으)로는 바꿀 수 없다 — %i %s", async (name, status, code) => {
  const res = await patch(name, "viewer");
  expect(res.status).toBe(status);
  expect((await res.json()).error.code).toBe(code);
});

it("같은 이름이면 그대로 돌려주고 감사도 남기지 않는다", async () => {
  const before = auditEntries.length;
  const res = await patch("viewer", "viewer");
  expect(await res.json()).toEqual({ username: "viewer", role: "viewer", can_operate: false });
  expect(auditEntries.length).toBe(before);
});

it("계정명을 바꾸면 계정·쿠키가 새 이름으로 옮겨지고 감사에 남는다", async () => {
  const res = await patch("viewer.kim", "viewer");
  expect(await res.json()).toEqual({ username: "viewer.kim", role: "viewer", can_operate: false });
  expect(res.headers.get("set-cookie")).toContain("metabole_admin=viewer.kim");
  expect([accounts.has("viewer"), accounts.get("viewer.kim")?.user.username]).toEqual([false, "viewer.kim"]);
  expect(auditEntries[0]).toMatchObject({ action: "username.change", target: "viewer.kim", detail: "viewer → viewer.kim" });
  await patch("viewer", "viewer.kim");
});
