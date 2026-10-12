import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { STREAM_RECOVER_MS, useChatStream } from "./use-chat-stream";

class FakeEventSource {
  static CLOSED = 2;
  static instances: FakeEventSource[] = [];
  readyState = 0;
  closed = false;
  onerror: (() => void) | null = null;
  listeners = new Map<string, (event: MessageEvent<string>) => void>();
  constructor(public url: string, public init?: EventSourceInit) {
    FakeEventSource.instances.push(this);
  }
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.set(type, listener);
  }
  emit(type: string, data: string) {
    this.listeners.get(type)?.({ data } as MessageEvent<string>);
  }
  close() {
    this.closed = true;
  }
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("채팅 실시간 연결", () => {
  it("로그인했을 때만 쿠키를 실어 연결하고, 메시지·삭제 이벤트를 넘겨준다", () => {
    const onEvent = vi.fn();
    const { rerender, unmount } = renderHook(({ on }) => useChatStream(on, { onEvent }), { initialProps: { on: false } });
    expect(FakeEventSource.instances).toHaveLength(0);
    rerender({ on: true });
    const [source] = FakeEventSource.instances;
    expect(source.url).toBe("/api/mock/chat/stream");
    expect(source.init).toEqual({ withCredentials: true });
    source.emit("message", JSON.stringify({ type: "message", room: "global", message_id: 1, message: {} }));
    source.emit("deleted", JSON.stringify({ type: "deleted", room: "global", message_id: 1, message: null }));
    source.emit("message", "{깨진");
    expect(onEvent.mock.calls.map(([event]) => event.type)).toEqual(["message", "deleted"]);
    unmount();
    expect(source.closed).toBe(true);
  });

  it("브라우저가 재접속을 포기하면 세션을 다시 확인하게 하고 잠시 뒤 새로 연결한다", () => {
    vi.useFakeTimers();
    const onLost = vi.fn();
    renderHook(() => useChatStream(true, { onEvent: vi.fn(), onLost }));
    const [first] = FakeEventSource.instances;
    first.readyState = 0;
    first.onerror?.();
    expect(onLost).not.toHaveBeenCalled(); // 아직 브라우저가 스스로 재접속하는 중
    first.readyState = FakeEventSource.CLOSED;
    first.onerror?.();
    expect(onLost).toHaveBeenCalledOnce();
    act(() => vi.advanceTimersByTime(STREAM_RECOVER_MS));
    expect(FakeEventSource.instances).toHaveLength(2);
  });
});
