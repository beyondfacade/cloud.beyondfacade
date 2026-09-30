import { expect, it } from "vitest";
import { accounts } from "../../users/store";
import { GET } from "./route";

const call = (cookie?: string) =>
  GET(new Request("http://test/api/mock/admin/auth/me", { headers: cookie ? { cookie } : {} }));

it("세션 쿠키가 없으면 401 UNAUTHENTICATED", async () => {
  const res = await call();
  expect(res.status).toBe(401);
  expect((await res.json()).error.code).toBe("UNAUTHENTICATED");
});

it("세션 쿠키의 계정과 등급을 돌려준다", async () => {
  const body = await (await call("theme=dark; metabole_admin=viewer")).json();
  expect(body).toEqual({ username: "viewer", role: "viewer", can_operate: false });
});

it("등급은 회원 목록에서 읽어 관리자 지정이 바로 반영된다", async () => {
  const account = accounts.get("viewer")!;
  const before = account.user;
  account.user = { ...before, role: "operator" };
  try {
    expect(await (await call("metabole_admin=viewer")).json()).toMatchObject({ role: "operator", can_operate: true });
  } finally {
    account.user = before;
  }
});

it("정지된 계정·없는 계정의 쿠키는 401", async () => {
  expect((await call("metabole_admin=kim.analyst")).status).toBe(401);
  expect((await call("metabole_admin=nobody")).status).toBe(401);
});
