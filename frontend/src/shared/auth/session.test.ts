import { QueryClient } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { fetchSession, loginHref, replaceSession, safeNext, SESSION_QUERY_KEY, signupHref } from "./session";

afterEach(() => vi.unstubAllGlobals());

const respond = (status: number, body: unknown) =>
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));

it("로그인돼 있으면 내 계정을, 비로그인(401)이면 null을 준다", async () => {
  respond(200, { username: "kim", role: "viewer", can_operate: false });
  expect(await fetchSession()).toEqual({ username: "kim", role: "viewer", can_operate: false });
  respond(401, { error: { code: "UNAUTHENTICATED", message: "로그인이 필요합니다." } });
  expect(await fetchSession()).toBeNull();
});

it("401이 아닌 오류는 그대로 던진다", async () => {
  respond(500, { error: { code: "INTERNAL", message: "x" } });
  await expect(fetchSession()).rejects.toMatchObject({ code: "INTERNAL" });
});

it("돌아갈 곳은 같은 사이트 경로만이고 로그인·가입 화면은 첫 화면으로 바꾼다", () => {
  expect(safeNext("/admin/security?tab=audit")).toBe("/admin/security?tab=audit");
  expect(safeNext("/map")).toBe("/map");
  expect(safeNext("https://evil.test")).toBe("/");
  expect(safeNext("//evil.test")).toBe("/");
  expect(safeNext("/\\evil.test")).toBe("/");
  expect(safeNext("/login?next=/admin")).toBe("/");
  expect(safeNext("/signup")).toBe("/");
  expect(safeNext(null)).toBe("/");
  expect(safeNext("/loginx")).toBe("/loginx");
});

it("로그인·가입 링크는 돌아올 경로를 인코딩해 싣는다", () => {
  expect(loginHref("/admin/users?user=kim")).toBe("/login?next=%2Fadmin%2Fusers%3Fuser%3Dkim");
  expect(signupHref("/map")).toBe("/signup?next=%2Fmap");
});

it("세션을 바꾸면 헤더 캐시는 새 값이 되고 관제실 캐시는 지워진다", () => {
  const client = new QueryClient();
  client.setQueryData(["admin", "security"], { stale: true });
  replaceSession(client, { username: "kim", role: "viewer", can_operate: false });
  expect(client.getQueryData(SESSION_QUERY_KEY)).toMatchObject({ username: "kim" });
  expect(client.getQueryData(["admin", "security"])).toBeUndefined();
});
