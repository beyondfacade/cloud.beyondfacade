// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

const fetchStub = vi.fn<typeof fetch>();
const context = { params: Promise.resolve({ id: "analysis-1" }) };
const url = "http://test/api/backend/analysis/analysis-1/events";

beforeEach(() => {
  vi.stubEnv("BACKEND_ORIGIN", "http://127.0.0.1:8201");
  vi.stubGlobal("fetch", fetchStub);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  fetchStub.mockReset();
});

describe("분석 SSE 프록시", () => {
  it("분석 식별자의 예약 문자를 인코딩해 하나의 업스트림 경로 구간으로 전달한다", async () => {
    fetchStub.mockResolvedValue(new Response(""));
    await GET(new Request(url), { params: Promise.resolve({ id: "analysis/1?view=full#part%" }) });
    expect(fetchStub).toHaveBeenCalledWith(
      "http://127.0.0.1:8201/analysis/analysis%2F1%3Fview%3Dfull%23part%25/events",
      expect.any(Object),
    );
  });

  it("스트림 종료를 기다리지 않고 업스트림 청크와 SSE 헤더를 그대로 전달한다", async () => {
    let controller!: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({ start(value) { controller = value; } });
    fetchStub.mockResolvedValue(new Response(stream));

    const request = new Request(url);
    const response = await GET(request, context);
    expect(response.status).toBe(200);
    expect(response.body).toBe(stream);
    expect(response.headers.get("content-type")).toBe("text/event-stream; charset=utf-8");
    expect(response.headers.get("cache-control")).toBe("no-cache, no-transform");
    expect(response.headers.get("connection")).toBe("keep-alive");
    expect(response.headers.get("x-accel-buffering")).toBe("no");
    expect(fetchStub).toHaveBeenCalledWith("http://127.0.0.1:8201/analysis/analysis-1/events", {
      headers: { accept: "text/event-stream" }, cache: "no-store", signal: request.signal,
    });

    const reader = response.body!.getReader();
    const first = new TextEncoder().encode('event: progress\ndata: {"step":1}\n\n');
    controller.enqueue(first);
    expect(await reader.read()).toEqual({ value: first, done: false });
    const second = new TextEncoder().encode('event: progress\ndata: {"step":2}\n\n');
    controller.enqueue(second);
    expect(await reader.read()).toEqual({ value: second, done: false });
    controller.close();
    expect(await reader.read()).toEqual({ value: undefined, done: true });
  });

  it("BACKEND_ORIGIN이 없으면 한국어 오류 본문과 404를 반환한다", async () => {
    vi.stubEnv("BACKEND_ORIGIN", undefined);
    const response = await GET(new Request(url), context);
    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({
      error: { code: "BACKEND_PROXY_DISABLED", message: expect.stringMatching(/[가-힣]/) },
    });
    expect(fetchStub).not.toHaveBeenCalled();
  });

  it.each([404, 500])("업스트림 %i 상태와 오류 본문을 그대로 전달한다", async (status) => {
    const body = '{"error":{"code":"UPSTREAM_ERROR","message":"분석 오류"}}';
    fetchStub.mockResolvedValue(new Response(body, { status }));
    const response = await GET(new Request(url), context);
    expect(response.status).toBe(status);
    expect(await response.text()).toBe(body);
  });

  it("클라이언트 연결 취소 신호를 진행 중인 업스트림 요청에 전달한다", async () => {
    const controller = new AbortController();
    const request = new Request(url, { signal: controller.signal });
    let resolveStarted!: (signal: AbortSignal) => void;
    const started = new Promise<AbortSignal>((resolve) => { resolveStarted = resolve; });
    fetchStub.mockImplementation((_input, init) => new Promise((_resolve, reject) => {
      const signal = init!.signal!;
      signal.addEventListener("abort", () => reject(signal.reason), { once: true });
      resolveStarted(signal);
    }));

    const response = GET(request, context);
    const signal = await Promise.race([started, response.then(() => null)]);
    expect(signal).toBe(request.signal);
    const rejected = expect(response).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    expect(signal!.aborted).toBe(true);
    await rejected;
  });
});
