import { expect, it } from "vitest";
import { DELETE } from "./[ip]/route";
import { GET, POST } from "./route";

const OPERATOR = { cookie: "metabole_admin=operator" };
const VIEWER = { cookie: "metabole_admin=viewer" };
const url = "http://test/api/mock/admin/security/ip-blocks";

const post = (body: unknown, headers: Record<string, string> = OPERATOR) =>
  POST(new Request(url, { method: "POST", headers, body: JSON.stringify(body) }));
const del = (ip: string, headers: Record<string, string> = OPERATOR) =>
  DELETE(new Request(`${url}/${ip}`, { method: "DELETE", headers }), { params: Promise.resolve({ ip }) });

it("비로그인은 목록 조회도 401", async () => {
  expect((await GET(new Request(url))).status).toBe(401);
});

it("운영 관리자가 차단하면 201과 함께 목록에 들어가고 해제하면 204", async () => {
  const created = await post({ ip: "192.0.2.44", reason: "테스트", ttl_minutes: 60 });
  expect(created.status).toBe(201);
  const block = await created.json();
  expect(block).toMatchObject({ ip: "192.0.2.44", created_by: "ops" });
  expect(block.expires_at).not.toBeNull();

  const list = await (await GET(new Request(url, { headers: VIEWER }))).json();
  expect(list.map((b: { ip: string }) => b.ip)).toContain("192.0.2.44");
  expect((await del("192.0.2.44")).status).toBe(204);
});

it("조회 관리자는 차단·해제 모두 403 FORBIDDEN_ROLE", async () => {
  const res = await post({ ip: "192.0.2.45", reason: "" }, VIEWER);
  expect(res.status).toBe(403);
  expect((await res.json()).error.code).toBe("FORBIDDEN_ROLE");
  expect((await del("198.51.100.7", VIEWER)).status).toBe(403);
});

it("형식이 틀린 IP는 400 INVALID_IP, 없는 IP 해제는 404", async () => {
  expect((await (await post({ ip: "999.1.1.1", reason: "" })).json()).error.code).toBe("INVALID_IP");
  const missing = await del("192.0.2.250");
  expect(missing.status).toBe(404);
  expect((await missing.json()).error.code).toBe("IP_BLOCK_NOT_FOUND");
});
