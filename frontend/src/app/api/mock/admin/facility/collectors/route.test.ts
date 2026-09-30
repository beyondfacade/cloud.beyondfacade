import { expect, it } from "vitest";
import { GET as getLog } from "./[key]/log/route";
import { POST as run } from "./[key]/run/route";
import { auditEntries } from "../../security/audit/store";

const OPERATOR = { cookie: "metabole_admin=operator" };
const VIEWER = { cookie: "metabole_admin=viewer" };
const base = "http://test/api/mock/admin/facility/collectors";
const ctx = (key: string) => ({ params: Promise.resolve({ key }) });

const log = (key: string, headers: Record<string, string> = OPERATOR, query = "") =>
  getLog(new Request(`${base}/${key}/log${query}`, { headers }), ctx(key));
const start = (key: string, headers: Record<string, string> = OPERATOR) =>
  run(new Request(`${base}/${key}/run`, { method: "POST", headers }), ctx(key));

it("로그와 실행은 운영 관리자만 — 비로그인 401, 조회 관리자 403", async () => {
  expect((await log("news-poller", {})).status).toBe(401);
  expect((await log("news-poller", VIEWER)).status).toBe(403);
  expect((await start("news-poller", VIEWER)).status).toBe(403);
});

it("로그는 요청한 줄 수만큼 꼬리를 주고 비밀값은 가려져 있다", async () => {
  const body = await (await log("funding-collector", OPERATOR, "?lines=10")).json();
  expect(body.lines).toHaveLength(10);
  expect(body.lines.at(-1)).toContain("serviceKey=***");
  expect(body).toMatchObject({ key: "funding-collector", log_file: "funding-collector.log", running: false });
});

it("모르는 수집기는 404 UNKNOWN_COLLECTOR", async () => {
  const res = await log("rm-rf");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("UNKNOWN_COLLECTOR");
});

it("수동 실행은 202이고 감사에 남으며 실행 중에 다시 누르면 409", async () => {
  const first = await start("rag-indexer");
  expect(first.status).toBe(202);
  expect(auditEntries[0]).toMatchObject({ action: "collector.run", target: "rag-indexer" });
  const again = await start("rag-indexer");
  expect(again.status).toBe(409);
  expect((await again.json()).error.code).toBe("COLLECTOR_RUNNING");
  expect((await (await log("rag-indexer")).json()).running).toBe(true);
});
