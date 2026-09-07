import { afterEach, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useAgentReport } from "./use-agent-report";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  onerror: (() => void) | null = null;
  closed = false;
  listeners = new Map<string, (e: MessageEvent) => void>();

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (e: MessageEvent) => void) {
    this.listeners.set(type, listener);
  }

  emit(type: string, data: string) {
    this.listeners.get(type)?.({ data } as MessageEvent);
  }

  close() {
    this.closed = true;
  }
}

function stubFetch(body: { analysis_id: string }) {
  const fetchMock = vi
    .fn()
    .mockImplementation(() => Promise.resolve(new Response(JSON.stringify(body), { status: 200 })));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

it("start()를 연속 호출해도 EventSource는 1개만 생성된다", async () => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);

  let resolvePost!: (body: { analysis_id: string }) => void;
  const postBody = new Promise<{ analysis_id: string }>((resolve) => {
    resolvePost = resolve;
  });
  const fetchMock = vi
    .fn()
    .mockImplementation(() => postBody.then((body) => new Response(JSON.stringify(body), { status: 200 })));
  vi.stubGlobal("fetch", fetchMock);

  const { result } = renderHook(() => useAgentReport());

  act(() => {
    result.current.start({ region: "1168064000", industry: "cafe" });
    result.current.start({ region: "1168064000", industry: "cafe" }); // 더블클릭 — 진행 중이므로 무시되어야 함
  });

  resolvePost({ analysis_id: "abc" });

  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("SSE payload가 JSON이 아니면 error 상태로 합류하고 스트림을 닫는다", async () => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);
  stubFetch({ analysis_id: "abc" });

  const { result } = renderHook(() => useAgentReport());

  act(() => {
    result.current.start({ region: "1168064000", industry: "cafe" });
  });
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));

  const source = FakeEventSource.instances[0];
  act(() => source.emit("agent_status", "not-json{"));

  expect(result.current.state.error).toBeTruthy();
  expect(source.closed).toBe(true);
  expect(result.current.loading).toBe(false);
});

it("NEXT_PUBLIC_API_BASE가 실 API여도 분석 요청·SSE는 mock 베이스를 유지한다", async () => {
  // RAG 분석 백엔드 미구현 — AI 분석 탭만 /api/mock 고정이 계약이다.
  vi.stubEnv("NEXT_PUBLIC_API_BASE", "http://localhost:8201");
  vi.resetModules();
  const { useAgentReport: freshUseAgentReport } = await import("./use-agent-report");

  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);
  const fetchMock = stubFetch({ analysis_id: "abc" });

  const { result } = renderHook(() => freshUseAgentReport());

  act(() => {
    result.current.start({ region: "1168064000", industry: "cafe" });
  });
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));

  expect(fetchMock.mock.calls[0][0]).toBe("/api/mock/analysis");
  expect(FakeEventSource.instances[0].url).toBe("/api/mock/analysis/abc/events");
});
