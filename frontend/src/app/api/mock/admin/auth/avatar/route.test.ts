import { expect, it } from "vitest";
import { PUT } from "./route";
import { GET } from "../avatars/[id]/route";
import { PATCH } from "../specialty/route";

const base = "http://test/api/mock/admin/auth";
const cookie = (user: string) => ({ cookie: `metabole_admin=${user}` });
const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0]);
const upload = (body: Uint8Array, user = "viewer") => PUT(new Request(`${base}/avatar`, { method: "PUT", headers: cookie(user), body }));
const specialty = (value: unknown, user: string) =>
  PATCH(new Request(`${base}/specialty`, { method: "PATCH", headers: { ...cookie(user), "content-type": "application/json" }, body: JSON.stringify({ specialty: value }) }));

it("사진을 올리면 버전이 오르고 회원 id 주소로 내려받는다", async () => {
  const first = await (await upload(PNG)).json();
  expect(first).toMatchObject({ id: 2, avatar_version: 1 });
  expect((await (await upload(PNG)).json()).avatar_version).toBe(2);

  const image = await GET(new Request(`${base}/avatars/2?v=2`, { headers: cookie("ops") }), { params: Promise.resolve({ id: "2" }) });
  expect(image.headers.get("content-type")).toBe("image/png");
  expect(new Uint8Array(await image.arrayBuffer())).toEqual(PNG);
});

it("이미지가 아니면 거절하고, 사진이 없으면 404", async () => {
  const res = await upload(new TextEncoder().encode("%PDF-1.4"));
  expect([res.status, (await res.json()).error.code]).toEqual([400, "INVALID_AVATAR"]);
  const none = await GET(new Request(`${base}/avatars/1`, { headers: cookie("ops") }), { params: Promise.resolve({ id: "1" }) });
  expect(none.status).toBe(404);
});

it("전문 업종은 전문가만 정하고 null로 비운다", async () => {
  expect((await specialty("카페", "viewer")).status).toBe(403);
  expect((await (await specialty(" 노래방 ", "park.expert")).json()).specialty).toBe("노래방");
  expect((await (await specialty(null, "park.expert")).json()).specialty).toBeNull();
  expect((await specialty("가".repeat(21), "park.expert")).status).toBe(400);
});
