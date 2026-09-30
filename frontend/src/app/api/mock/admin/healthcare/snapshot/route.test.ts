import { expect, it } from "vitest";
import { GET } from "./route";

const call = (cookie?: string) =>
  GET(new Request("http://test/api/mock/admin/healthcare/snapshot", { headers: cookie ? { cookie } : {} }));

it("비로그인은 401", async () => {
  expect((await call()).status).toBe(401);
});

it("LLM 경로는 primary 다음 fallback 순서이고 RAG 집계 합이 맞는다", async () => {
  const body = await (await call("metabole_admin=viewer")).json();
  expect(body.llm_routes.map((r: { role: string }) => r.role)).toEqual(["primary", "fallback"]);
  const sum = body.rag.by_source.reduce((acc: number, s: { chunks: number }) => acc + s.chunks, 0);
  expect(sum).toBe(body.rag.total_chunks);
  expect(body.usage_24h.window_hours).toBe(24);
});
