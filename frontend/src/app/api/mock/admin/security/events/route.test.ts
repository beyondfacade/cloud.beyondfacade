import { expect, it } from "vitest";
import { GET } from "./route";

const VIEWER = { cookie: "metabole_admin=viewer" };
const get = (query = "", headers: Record<string, string> = VIEWER) =>
  GET(new Request(`http://test/api/mock/admin/security/events${query}`, { headers }));

it("비로그인은 401", async () => {
  expect((await get("", {})).status).toBe(401);
});

it("기본 한 쪽은 최신순 50건이고 next_before_id로 다음 쪽을 잇는다", async () => {
  const first = await (await get()).json();
  expect(first.items).toHaveLength(50);
  expect(first.items[0].id).toBeGreaterThan(first.items[1].id);
  expect(first.next_before_id).toBe(first.items[49].id);
  const second = await (await get(`?before_id=${first.next_before_id}`)).json();
  expect(second.items[0].id).toBeLessThan(first.next_before_id);
});

it("종류와 IP로 거른다", async () => {
  const body = await (await get("?kind=scanner_probe&ip=198.51.100.7")).json();
  expect(body.items.length).toBeGreaterThan(0);
  expect(body.items.every((e: { kind: string; ip: string }) => e.kind === "scanner_probe" && e.ip === "198.51.100.7")).toBe(true);
});

it("모르는 종류는 422", async () => {
  expect((await get("?kind=nope")).status).toBe(422);
});
