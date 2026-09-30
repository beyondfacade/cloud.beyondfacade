import { expect, it } from "vitest";
import { accounts } from "../../users/store";
import { GET as callback } from "./callback/route";
import { GET as start } from "./start/route";

const base = "http://test/api/mock/admin/auth/google";

async function begin(next: string) {
  const res = await start(new Request(`${base}/start?next=${encodeURIComponent(next)}`));
  const cookie = res.headers.get("set-cookie")!.split(";")[0];
  return { res, cookie, location: res.headers.get("location")! };
}

it("시작은 state를 쿠키에 싣고 302로 넘긴다", async () => {
  const { res, cookie, location } = await begin("/admin");
  expect(res.status).toBe(302);
  expect(cookie).toMatch(/^metabole_oauth=/);
  expect(location).toMatch(/\/google\/callback\?code=.+&state=.+/);
});

it("콜백은 구글 계정을 일반 등급으로 만들고 세션 쿠키를 심어 next로 보낸다", async () => {
  const { cookie, location } = await begin("/admin/security");
  const res = await callback(new Request(`http://test${location}`, { headers: { cookie } }));
  expect(res.status).toBe(302);
  expect(res.headers.get("location")).toBe("/admin/security");
  expect(res.headers.get("set-cookie")).toMatch(/metabole_admin=google\.user; HttpOnly/);
  expect(accounts.get("google.user")?.user).toMatchObject({ role: "viewer", has_password: false, has_google: true });
});

it("외부 next는 첫 화면으로 바꾼다", async () => {
  const { cookie, location } = await begin("//evil.test");
  const res = await callback(new Request(`http://test${location}`, { headers: { cookie } }));
  expect(res.headers.get("location")).toBe("/");
});

it("state가 다르면 세션 없이 로그인 화면으로 이유를 달아 보낸다", async () => {
  const { cookie } = await begin("/admin");
  const res = await callback(new Request(`${base}/callback?code=x&state=forged`, { headers: { cookie } }));
  expect(res.headers.get("location")).toBe("/login?error=OAUTH_STATE_MISMATCH");
  expect(res.headers.get("set-cookie")).not.toMatch(/metabole_admin=/);
});

it("구글에서 취소해 code가 없으면 GOOGLE_LOGIN_FAILED", async () => {
  const { cookie } = await begin("/admin");
  const res = await callback(new Request(`${base}/callback?error=access_denied&state=mock-state`, { headers: { cookie } }));
  expect(res.headers.get("location")).toBe("/login?error=GOOGLE_LOGIN_FAILED");
});
