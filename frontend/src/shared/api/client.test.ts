import { afterEach, expect, it, vi } from "vitest";
import { apiGet, apiPost, ApiError } from "./client";

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
