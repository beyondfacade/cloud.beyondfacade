import { expect, it } from "vitest";
import { auditEntries } from "../../audit/store";
import { GET, PUT } from "./route";

const OPERATOR = { cookie: "metabole_admin=operator" };
const VIEWER = { cookie: "metabole_admin=viewer" };
const url = "http://test/api/mock/admin/security/settings/auto-defense";

const put = (body: unknown, headers: Record<string, string> = OPERATOR) =>
  PUT(new Request(url, { method: "PUT", headers, body: JSON.stringify(body) }));

it("비로그인은 조회도 401", async () => {
  expect((await GET(new Request(url))).status).toBe(401);
});

it("기본값은 켜짐이고 일반 회원도 규칙 목록을 본다", async () => {
  const body = await (await GET(new Request(url, { headers: VIEWER }))).json();
  expect(body.enabled).toBe(true);
  expect(body.rules.map((r: { rule: string }) => r.rule)).toEqual(["brute_force_login", "scanner_probe"]);
  expect(body.rules[0]).toMatchObject({ threshold: 10, window_minutes: 15, block_minutes: 60, repeat_block_minutes: 1_440 });
});

it("일반 회원이 바꾸려 하면 403 FORBIDDEN_ROLE", async () => {
  const res = await put({ enabled: false }, VIEWER);
  expect(res.status).toBe(403);
  expect((await res.json()).error.code).toBe("FORBIDDEN_ROLE");
});

it("관리자가 끄고 켜면 처리자가 남고 감사 로그에 기록된다", async () => {
  const off = await (await put({ enabled: false })).json();
  expect(off).toMatchObject({ enabled: false, updated_by: "ops" });
  expect(auditEntries[0]).toMatchObject({ action: "auto_defense.toggle", target: "auto_defense", detail: "끔" });

  const on = await (await put({ enabled: true })).json();
  expect(on.enabled).toBe(true);
  expect(auditEntries[0].detail).toBe("켬");
});

it("enabled가 불리언이 아니면 422 VALIDATION_ERROR", async () => {
  const res = await put({ enabled: "off" });
  expect(res.status).toBe(422);
  expect((await res.json()).error.code).toBe("VALIDATION_ERROR");
});
