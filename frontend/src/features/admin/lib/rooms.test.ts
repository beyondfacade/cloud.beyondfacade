import { expect, it } from "vitest";
import { ROOMS, ROOM_BY_KEY, safeAdminNext } from "./rooms";

it("방 3종은 보안·헬스케어·설비 순서이고 모두 /admin 아래다", () => {
  expect(ROOMS.map((r) => r.key)).toEqual(["security", "healthcare", "facility"]);
  expect(ROOMS.every((r) => r.href.startsWith("/admin/"))).toBe(true);
  expect(ROOM_BY_KEY.facility.pollMs).toBeLessThan(ROOM_BY_KEY.security.pollMs);
});

it("로그인 후 복귀 경로는 관리자 내부만 허용한다", () => {
  expect(safeAdminNext("/admin/security")).toBe("/admin/security");
  expect(safeAdminNext("/admin/facility?tab=db")).toBe("/admin/facility?tab=db");
  expect(safeAdminNext("https://evil.test")).toBe("/admin");
  expect(safeAdminNext("//evil.test/admin")).toBe("/admin");
  expect(safeAdminNext("/map")).toBe("/admin");
  expect(safeAdminNext("/admin/login")).toBe("/admin");
  expect(safeAdminNext(null)).toBe("/admin");
});
