// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

const fetchStub = vi.fn<typeof fetch>();
const url = "http://test/api/backend/chat/stream";

beforeEach(() => {
  vi.stubEnv("BACKEND_ORIGIN", "http://127.0.0.1:8201");
  vi.stubGlobal("fetch", fetchStub);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  fetchStub.mockReset();
});

describe("채팅 SSE 프록시", () => {
  it("로그인 쿠키와 Last-Event-ID를 넘기고 스트림을 그대로 흘려보낸다", async () => {
    const stream = new ReadableStream<Uint8Array>();
    fetchStub.mockResolvedValue(new Response(stream));
    const request = new Request(url, { headers: { cookie: "metabole_admin=abc", "last-event-id": "42", "x-other": "1" } });
    const response = await GET(request);
    expect(response.body).toBe(stream);
    expect(response.headers.get("content-type")).toBe("text/event-stream; charset=utf-8");
    expect(response.headers.get("x-accel-buffering")).toBe("no");
    expect(fetchStub).toHaveBeenCalledWith("http://127.0.0.1:8201/chat/stream", {
      headers: { accept: "text/event-stream", cookie: "metabole_admin=abc", "last-event-id": "42" },
      cache: "no-store",
      signal: request.signal,
    });
  });

  it("처음 연결이면 Last-Event-ID 없이 보낸다", async () => {
    fetchStub.mockResolvedValue(new Response(""));
    await GET(new Request(url, { headers: { cookie: "metabole_admin=abc" } }));
    expect(fetchStub.mock.calls[0][1]).toMatchObject({ headers: { accept: "text/event-stream", cookie: "metabole_admin=abc" } });
  });

  it("비로그인 401은 상태 코드를 그대로 돌려줘 브라우저가 재접속을 멈추게 한다", async () => {
    fetchStub.mockResolvedValue(Response.json({ error: { code: "UNAUTHENTICATED" } }, { status: 401 }));
    const response = await GET(new Request(url));
    expect(response.status).toBe(401);
    expect(response.headers.get("content-type")).toBe("application/json");
  });

  it("BACKEND_ORIGIN이 없으면 한국어 오류 본문과 404를 반환한다", async () => {
    vi.stubEnv("BACKEND_ORIGIN", undefined);
    const response = await GET(new Request(url));
    expect(response.status).toBe(404);
    expect((await response.json()).error.message).toBe("백엔드 프록시가 설정되지 않았습니다.");
  });
});
