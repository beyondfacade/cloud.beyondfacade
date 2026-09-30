import { expect, it } from "vitest";
import { PUT as resetPassword } from "./[username]/password/route";
import { PATCH as changeRole } from "./[username]/role/route";
import { DELETE as revokeSessions, GET as getSessions } from "./[username]/sessions/route";
import { PATCH as setStatus } from "./[username]/status/route";
import { GET, POST } from "./route";
import { auditEntries } from "../security/audit/store";

const OPERATOR = { cookie: "metabole_admin=operator" };
const VIEWER = { cookie: "metabole_admin=viewer" };
const base = "http://test/api/mock/admin/users";
const ctx = (username: string) => ({ params: Promise.resolve({ username }) });
const json = (method: string, body: unknown, headers: Record<string, string> = OPERATOR) => ({
  method, headers: { ...headers, "content-type": "application/json" }, body: JSON.stringify(body),
});

const list = (query = "", headers: Record<string, string> = VIEWER) => GET(new Request(`${base}${query}`, { headers }));
const names = async (query: string) =>
  ((await (await list(query)).json()).items as { username: string }[]).map((u) => u.username);

it("비로그인은 목록도 401", async () => {
  expect((await list("", {})).status).toBe(401);
});

it("목록은 계정명순이고 비밀번호 해시 같은 필드는 없다", async () => {
  const { items } = await (await list()).json();
  expect(items.map((u: { username: string }) => u.username)).toEqual(["kim.analyst", "lee.ops", "ops", "viewer"]);
  expect(Object.keys(items[0]).sort()).toEqual(
    ["active_sessions", "created_at", "email", "has_google", "has_password", "is_active", "last_login_at", "role", "username"],
  );
});

it("검색어·역할·상태로 거른다", async () => {
  expect(await names("?q=OPS")).toEqual(["lee.ops", "ops"]);
  expect(await names("?role=viewer")).toEqual(["kim.analyst", "viewer"]);
  expect(await names("?status=suspended")).toEqual(["kim.analyst"]);
});

it("계정 생성은 운영 관리자만, 규칙 위반은 실 API와 같은 코드로 거절한다", async () => {
  expect((await POST(new Request(base, json("POST", { username: "new.one", role: "viewer", password: "long-enough-pass" }, VIEWER)))).status).toBe(403);
  const code = async (body: unknown) => (await (await POST(new Request(base, json("POST", body)))).json()).error.code;
  expect(await code({ username: "Bad Name", role: "viewer", password: "long-enough-pass" })).toBe("INVALID_USERNAME");
  expect(await code({ username: "short.pw", role: "viewer", password: "short" })).toBe("WEAK_PASSWORD");
  expect(await code({ username: "viewer", role: "viewer", password: "long-enough-pass" })).toBe("USERNAME_TAKEN");
  const created = await POST(new Request(base, json("POST", { username: "new.one", role: "viewer", password: "long-enough-pass" })));
  expect(created.status).toBe(201);
  expect(auditEntries[0]).toMatchObject({ action: "user.create", target: "new.one" });
});

it("역할 변경과 정지·재개는 감사에 남고 정지하면 세션이 0이 된다", async () => {
  const role = await changeRole(new Request(`${base}/viewer/role`, json("PATCH", { role: "operator" })), ctx("viewer"));
  expect((await role.json()).role).toBe("operator");
  const suspended = await (await setStatus(new Request(`${base}/viewer/status`, json("PATCH", { active: false })), ctx("viewer"))).json();
  expect([suspended.is_active, suspended.active_sessions]).toEqual([false, 0]);
  await setStatus(new Request(`${base}/viewer/status`, json("PATCH", { active: true })), ctx("viewer"));
  await changeRole(new Request(`${base}/viewer/role`, json("PATCH", { role: "viewer" })), ctx("viewer"));
  expect(auditEntries.slice(0, 3).map((e) => e.action)).toEqual(["user.role", "user.reactivate", "user.suspend"]);
});

it("자기 계정 변경은 400 SELF_CHANGE, 없는 계정은 404", async () => {
  const self = await changeRole(new Request(`${base}/ops/role`, json("PATCH", { role: "viewer" })), ctx("ops"));
  expect((await self.json()).error.code).toBe("SELF_CHANGE");
  const ghost = await setStatus(new Request(`${base}/ghost/status`, json("PATCH", { active: false })), ctx("ghost"));
  expect(ghost.status).toBe(404);
});

it("비밀번호 재설정은 204이고 12자 미만은 WEAK_PASSWORD", async () => {
  const weak = await resetPassword(new Request(`${base}/lee.ops/password`, json("PUT", { password: "short" })), ctx("lee.ops"));
  expect((await weak.json()).error.code).toBe("WEAK_PASSWORD");
  const ok = await resetPassword(new Request(`${base}/lee.ops/password`, json("PUT", { password: "brand-new-password" })), ctx("lee.ops"));
  expect(ok.status).toBe(204);
});

it("세션은 본인 또는 운영 관리자만 보고, 본인이 끊으면 지금 세션은 남는다", async () => {
  expect((await getSessions(new Request(`${base}/ops/sessions`, { headers: VIEWER }), ctx("ops"))).status).toBe(403);
  const mine = await (await getSessions(new Request(`${base}/ops/sessions`, { headers: OPERATOR }), ctx("ops"))).json();
  expect(mine.items[0].current).toBe(true);
  const revoked = await (await revokeSessions(new Request(`${base}/ops/sessions`, { method: "DELETE", headers: OPERATOR }), ctx("ops"))).json();
  expect(revoked.revoked).toBe(mine.items.length - 1);
});
