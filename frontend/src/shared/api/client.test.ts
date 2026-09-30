import { afterEach, expect, it, vi } from "vitest";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, ApiError } from "./client";

afterEach(() => vi.restoreAllMocks());

it("정상 응답은 JSON을 반환한다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ ok: 1 }), { status: 200 })));
  await expect(apiGet("/x")).resolves.toEqual({ ok: 1 });
});

it("에러 응답은 {error:{code,message}}를 ApiError로 던진다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: "없음" } }), { status: 404 })));
  await expect(apiGet("/x")).rejects.toMatchObject({ code: "NOT_FOUND", message: "없음" });
  await expect(apiGet("/x")).rejects.toBeInstanceOf(ApiError);
});

it("본문 없는 204 응답은 undefined로 끝난다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
  await expect(apiPost("/x", {})).resolves.toBeUndefined();
});

it("DELETE는 메서드를 실어 보내고 에러 바디를 ApiError로 던진다", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ error: { code: "IP_BLOCK_NOT_FOUND", message: "없음" } }), { status: 404 }));
  vi.stubGlobal("fetch", fetchMock);
  await expect(apiDelete("/x/1")).rejects.toMatchObject({ code: "IP_BLOCK_NOT_FOUND" });
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "DELETE" });
});

it("PATCH와 PUT은 메서드와 JSON 본문을 실어 보낸다", async () => {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ ok: 1 }), { status: 200 })));
  vi.stubGlobal("fetch", fetchMock);
  await apiPatch("/x", { role: "viewer" });
  await apiPut("/x", { password: "p" });
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "PATCH", body: JSON.stringify({ role: "viewer" }) });
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "PUT" });
});

it("선택적 요청 신호가 GET과 POST의 실제 fetch를 중단한다", async () => {
  const fetchMock = vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
    init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  }));
  vi.stubGlobal("fetch", fetchMock);
  const getController = new AbortController();
  const postController = new AbortController();
  const getRequest = apiGet("/x", { signal: getController.signal });
  const postRequest = apiPost("/x", { text: "안녕" }, undefined, { signal: postController.signal });

  getController.abort();
  postController.abort();
  await expect(getRequest).rejects.toMatchObject({ name: "AbortError" });
  await expect(postRequest).rejects.toMatchObject({ name: "AbortError" });
});
