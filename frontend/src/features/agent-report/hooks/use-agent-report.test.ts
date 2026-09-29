import { afterEach, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReportFacts } from "@/shared/api/types";
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

it("SSE facts 이벤트를 받으면 훅 상태에 사실이 저장된다", async () => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);
  stubFetch({ analysis_id: "abc" });
  const unavailable = { available: false, reason: "자료 없음" } as const;
  const facts: ReportFacts = {
    region: { code: "1168064000", name: "역삼1동", industry_id: "cafe", industry_name: "카페" },
    verdict: unavailable, alternatives: unavailable, profile: unavailable,
    hour_gap: unavailable, commerce_change: unavailable, metrics_history: unavailable,
    population: unavailable, shocks: unavailable, news: unavailable, funding_candidates: unavailable,
    budget: null,
  };
  const { result } = renderHook(() => useAgentReport());

  await act(() => result.current.start({ region: "1168064000", industry: "cafe" }));
  act(() => FakeEventSource.instances[0].emit("facts", JSON.stringify({ type: "facts", facts })));

  expect(result.current.state.facts).toEqual(facts);
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

it("SSE onerror 시 running 에이전트 슬롯을 error로 내린다", async () => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);
  stubFetch({ analysis_id: "abc" });

  const { result } = renderHook(() => useAgentReport());

  act(() => {
    result.current.start({ region: "1168064000", industry: "cafe" });
  });
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));

  const source = FakeEventSource.instances[0];
  act(() =>
    source.emit(
      "agent_status",
      JSON.stringify({ type: "agent_status", agent: "orchestrator", status: "running" }),
    ),
  );
  expect(result.current.state.agents.orchestrator.status).toBe("running");

  act(() => source.onerror?.());

  expect(result.current.state.error).toBeTruthy();
  expect(result.current.state.agents.orchestrator.status).toBe("error");
  expect(result.current.loading).toBe(false);
  expect(source.closed).toBe(true);
});

it("분석 POST·SSE는 config.apiBase(NEXT_PUBLIC_API_BASE)를 따른다", async () => {
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

  expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8201/analysis");
  expect(FakeEventSource.instances[0].url).toBe("http://localhost:8201/analysis/abc/events");
});

it.each([undefined, 0, 50_000_000])("분석 요청은 선택 예산 %s를 원 단위 그대로 전달한다", async (budget) => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  const fetchMock = stubFetch({ analysis_id: "abc" });
  const { result } = renderHook(() => useAgentReport());
  await act(() => result.current.start({ region: "1168064000", industry: "cafe", budget }));
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
    region: "1168064000", industry: "cafe", ...(budget === undefined ? {} : { budget }),
  });
});

it("자동 시작 POST가 끝나기 전에 화면을 떠나면 늦은 응답으로 스트림을 열지 않는다", async () => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  let resolvePost!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { resolvePost = resolve; })));
  const { result, unmount } = renderHook(() => useAgentReport());
  let pending!: Promise<void>;
  act(() => { pending = result.current.start({ region: "1168064000", industry: "cafe" }); });
  unmount();
  await act(async () => {
    resolvePost(Response.json({ analysis_id: "late" }));
    await pending;
  });
  expect(FakeEventSource.instances).toHaveLength(0);
});
