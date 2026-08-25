import { afterEach, expect, it, vi } from "vitest";
import { apiGet, ApiError } from "./client";

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
