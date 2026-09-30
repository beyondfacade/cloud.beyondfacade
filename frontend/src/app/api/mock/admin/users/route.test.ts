import { expect, it } from "vitest";
import { DELETE as revokeSessions, GET as getSessions } from "./[username]/sessions/route";
import { PATCH as setStatus } from "./[username]/status/route";
import * as usersRoute from "./route";
import { auditEntries } from "../security/audit/store";

const { GET } = usersRoute;
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

it("실 API처럼 화면에서 계정을 만들 수 없다 — POST 핸들러가 없다", () => {
  expect("POST" in usersRoute).toBe(false);
});

it("정지·재개는 관리자만, 감사에 남고 정지하면 세션이 0이 된다", async () => {
  expect((await setStatus(new Request(`${base}/viewer/status`, json("PATCH", { active: false }, VIEWER)), ctx("viewer"))).status).toBe(403);
  const suspended = await (await setStatus(new Request(`${base}/viewer/status`, json("PATCH", { active: false })), ctx("viewer"))).json();
  expect([suspended.is_active, suspended.active_sessions]).toEqual([false, 0]);
  await setStatus(new Request(`${base}/viewer/status`, json("PATCH", { active: true })), ctx("viewer"));
  expect(auditEntries.slice(0, 2).map((e) => e.action)).toEqual(["user.reactivate", "user.suspend"]);
});

it("내 계정 정지는 400 SELF_CHANGE, 없는 계정은 404", async () => {
  const self = await setStatus(new Request(`${base}/ops/status`, json("PATCH", { active: false })), ctx("ops"));
  expect((await self.json()).error).toEqual({ code: "SELF_CHANGE", message: "내 계정은 여기서 정지할 수 없습니다." });
  const ghost = await setStatus(new Request(`${base}/ghost/status`, json("PATCH", { active: false })), ctx("ghost"));
  expect(ghost.status).toBe(404);
});

it("세션은 본인 또는 운영 관리자만 보고, 본인이 끊으면 지금 세션은 남는다", async () => {
  expect((await getSessions(new Request(`${base}/ops/sessions`, { headers: VIEWER }), ctx("ops"))).status).toBe(403);
  const mine = await (await getSessions(new Request(`${base}/ops/sessions`, { headers: OPERATOR }), ctx("ops"))).json();
  expect(mine.items[0].current).toBe(true);
  const revoked = await (await revokeSessions(new Request(`${base}/ops/sessions`, { method: "DELETE", headers: OPERATOR }), ctx("ops"))).json();
  expect(revoked.revoked).toBe(mine.items.length - 1);
});
