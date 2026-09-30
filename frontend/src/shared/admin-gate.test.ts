import { expect, it } from "vitest";
import { adminGateRedirect, ADMIN_SESSION_COOKIE } from "./admin-gate";

it("세션 쿠키 이름은 백엔드와 같다", () => {
  expect(ADMIN_SESSION_COOKIE).toBe("metabole_admin");
});

it("쿠키 없이 관리자 방에 들어오면 돌아올 경로를 달고 로그인으로 보낸다", () => {
  expect(adminGateRedirect("/admin/security", "", false)).toBe("/admin/login?next=%2Fadmin%2Fsecurity");
  expect(adminGateRedirect("/admin/facility", "?tab=db", false)).toBe("/admin/login?next=%2Fadmin%2Ffacility%3Ftab%3Ddb");
});

it("쿠키가 있으면 통과시킨다 — 실제 검증은 백엔드가 한다", () => {
  expect(adminGateRedirect("/admin/security", "", true)).toBeNull();
});

it("로그인 화면 자체는 막지 않는다", () => {
  expect(adminGateRedirect("/admin/login", "", false)).toBeNull();
});
