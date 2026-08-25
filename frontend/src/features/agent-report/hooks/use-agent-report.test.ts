import { afterEach, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useAgentReport } from "./use-agent-report";

afterEach(() => vi.restoreAllMocks());

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  onerror: (() => void) | null = null;
  closed = false;

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener() {
    // 이 테스트는 재진입 가드만 검증 — 이벤트 전달은 불필요.
  }

  close() {
    this.closed = true;
  }
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
