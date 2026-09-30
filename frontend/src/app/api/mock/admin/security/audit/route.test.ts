import { expect, it } from "vitest";
import { GET } from "./route";

const VIEWER = { cookie: "metabole_admin=viewer" };
const get = (query = "", headers: Record<string, string> = VIEWER) =>
  GET(new Request(`http://test/api/mock/admin/security/audit${query}`, { headers }));

it("비로그인은 401", async () => {
  expect((await get("", {})).status).toBe(401);
});

it("조회 관리자도 최신순 감사 로그를 받는다", async () => {
  const body = await (await get()).json();
  expect(body.items[0]).toMatchObject({ action: expect.any(String), actor: expect.any(String), target: expect.any(String) });
  expect(body.next_before_id).toBeNull();
});

it("조치별로 거르고 limit으로 쪽을 나눈다", async () => {
  const filtered = await (await get("?action=ip_block.create")).json();
  expect(filtered.items.every((e: { action: string }) => e.action === "ip_block.create")).toBe(true);
  const paged = await (await get("?limit=1")).json();
  expect(paged.items).toHaveLength(1);
  expect(paged.next_before_id).toBe(paged.items[0].id);
});
