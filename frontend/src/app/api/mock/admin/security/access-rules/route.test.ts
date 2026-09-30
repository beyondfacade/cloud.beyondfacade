import { expect, it } from "vitest";
import { auditEntries } from "../audit/store";
import { DELETE } from "./[id]/route";
import { GET as currentDevice } from "./current-device/route";
import { GET, POST } from "./route";

const OPERATOR = { cookie: "metabole_admin=operator" };
const VIEWER = { cookie: "metabole_admin=viewer" };
const url = "http://test/api/mock/admin/security/access-rules";

const post = (body: unknown, headers: Record<string, string> = OPERATOR) =>
  POST(new Request(url, { method: "POST", headers, body: JSON.stringify(body) }));
const del = (id: number, headers: Record<string, string> = OPERATOR) =>
  DELETE(new Request(`${url}/${id}`, { method: "DELETE", headers }), { params: Promise.resolve({ id: String(id) }) });
const rule = (overrides: Record<string, unknown>) => ({ policy: "allow", target: "ip", value: "", note: "", ttl_minutes: null, ...overrides });

it("비로그인은 목록 조회도 401", async () => {
  expect((await GET(new Request(url))).status).toBe(401);
});

it("일반 회원은 목록을 보고, 추가·삭제는 403 FORBIDDEN_ROLE", async () => {
  const list = await (await GET(new Request(url, { headers: VIEWER }))).json();
  expect(list.map((r: { value: string }) => r.value)).toContain("10.0.0.0/8");
  const res = await post(rule({ value: "192.0.2.0/24" }), VIEWER);
  expect(res.status).toBe(403);
  expect((await res.json()).error.code).toBe("FORBIDDEN_ROLE");
  expect((await del(1, VIEWER)).status).toBe(403);
});

it("관리자가 화이트리스트에 대역을 넣고 지우면 감사 로그에 남는다", async () => {
  const created = await post(rule({ value: " 192.0.2.0/24 ", note: "지점" }));
  expect(created.status).toBe(201);
  const body = await created.json();
  expect(body).toMatchObject({ policy: "allow", target: "ip", value: "192.0.2.0/24", note: "지점", created_by: "ops", expires_at: null });
  expect(auditEntries[0]).toMatchObject({ action: "access_rule.create", target: "192.0.2.0/24" });

  expect((await del(body.id)).status).toBe(204);
  expect(auditEntries[0]).toMatchObject({ action: "access_rule.delete", target: "192.0.2.0/24" });
  const missing = await del(body.id);
  expect(missing.status).toBe(404);
  expect((await missing.json()).error.code).toBe("ACCESS_RULE_NOT_FOUND");
});

it("형식이 틀린 값·너무 넓은 대역·IP 블랙리스트는 400 INVALID_ACCESS_RULE", async () => {
  for (const body of [rule({ value: "abc" }), rule({ value: "0.0.0.0/0" }), rule({ target: "device", value: "short" }), rule({ policy: "deny", value: "192.0.2.1" })]) {
    const res = await post(body);
    expect(res.status).toBe(400);
    expect((await res.json()).error.code).toBe("INVALID_ACCESS_RULE");
  }
});

it("이미 있는 값은 409, 지금 내 디바이스를 차단하면 400 SELF_BLOCK", async () => {
  expect((await (await post(rule({ value: "10.0.0.0/8" }))).json()).error.code).toBe("ACCESS_RULE_EXISTS");
  const me = await (await currentDevice(new Request(`${url}/current-device`, { headers: OPERATOR }))).json();
  const res = await post(rule({ policy: "deny", target: "device", value: me.device_id }));
  expect((await res.json()).error.code).toBe("SELF_BLOCK");
});

it("지금 디바이스 조회는 ID·브라우저와 목록 상태를 돌려준다", async () => {
  const me = await (await currentDevice(new Request(`${url}/current-device`, { headers: VIEWER }))).json();
  expect(me.device_id).toMatch(/^[A-Za-z0-9_-]{22}$/);
  expect(me).toMatchObject({ allowed: false, denied: false });
});
