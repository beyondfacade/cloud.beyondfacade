import { expect, it } from "vitest";
import { POST } from "./route";

const call = (body: unknown, cookie = "metabole_admin=operator") =>
  POST(new Request("http://test/api/mock/admin/healthcare/probe", {
    method: "POST", headers: { cookie }, body: JSON.stringify(body),
  }));

it("RAG 프로브는 검색 결과를, LLM 프로브는 답한 모델과 출력을 준다", async () => {
  const rag = await (await call({ kind: "rag", message: "임대료" })).json();
  expect(rag).toMatchObject({ kind: "rag", ok: true });
  expect(rag.hits.length).toBeGreaterThan(0);
  const llm = await (await call({ kind: "llm", message: "안녕" })).json();
  expect(llm.model).toBe("gemini-2.5-flash");
  expect(llm.output).toContain("안녕");
});

it("조회 관리자는 403 — 프로브는 실제 호출 비용이 든다", async () => {
  expect((await call({ kind: "llm", message: "x" }, "metabole_admin=viewer")).status).toBe(403);
});

it("모르는 kind는 422", async () => {
  expect((await call({ kind: "sql", message: "x" })).status).toBe(422);
});
