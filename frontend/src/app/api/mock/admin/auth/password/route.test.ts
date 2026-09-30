import { expect, it } from "vitest";
import { POST } from "./route";
import { auditEntries } from "../../security/audit/store";
import { accounts } from "../../users/store";

const url = "http://test/api/mock/admin/auth/password";
const post = (body: unknown, headers: Record<string, string> = { cookie: "metabole_admin=viewer" }) =>
  POST(new Request(url, { method: "POST", headers, body: JSON.stringify(body) }));

it("비로그인은 401", async () => {
  expect((await post({ current_password: "x", new_password: "long-enough-pass" }, {})).status).toBe(401);
});

it("현재 비밀번호가 틀리거나 비어 있으면 400 WRONG_PASSWORD — 401이 아니다", async () => {
  for (const current of ["wrong", ""]) {
    const res = await post({ current_password: current, new_password: "long-enough-pass" });
    expect(res.status).toBe(400);
    expect((await res.json()).error.code).toBe("WRONG_PASSWORD");
  }
});

it("새 비밀번호가 12자 미만이면 WEAK_PASSWORD, 맞으면 204", async () => {
  expect((await (await post({ current_password: "old-password", new_password: "short" })).json()).error.code).toBe("WEAK_PASSWORD");
  expect((await post({ current_password: "old-password", new_password: "long-enough-pass" })).status).toBe(204);
});

it("비밀번호가 없는 구글 전용 계정은 현재 비밀번호 없이 처음 설정한다", async () => {
  const google = accounts.get("kim.analyst")!;
  google.user = { ...google.user, is_active: true };
  const res = await post({ current_password: "", new_password: "long-enough-pass" }, { cookie: "metabole_admin=kim.analyst" });
  expect(res.status).toBe(204);
  expect(accounts.get("kim.analyst")!.user.has_password).toBe(true);
  expect(auditEntries[0]).toMatchObject({ action: "password.change", target: "kim.analyst", detail: "처음 설정" });
});
