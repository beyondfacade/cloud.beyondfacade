import { expect, it } from "vitest";
import { ROOMS, ROOM_BY_KEY } from "./rooms";

it("방 4종은 보안·헬스케어·설비·인사 순서이고 모두 /admin 아래다", () => {
  expect(ROOMS.map((r) => r.key)).toEqual(["security", "healthcare", "facility", "users"]);
  expect(ROOMS.every((r) => r.href.startsWith("/admin/"))).toBe(true);
  expect(ROOM_BY_KEY.facility.pollMs).toBeLessThan(ROOM_BY_KEY.security.pollMs);
});
