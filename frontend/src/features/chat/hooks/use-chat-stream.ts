"use client";

import { useEffect, useRef } from "react";
import type { ChatEvent } from "@/shared/api/types";
import { chatStreamUrl } from "../api";

export const STREAM_RECOVER_MS = 10_000;

interface Handlers {
  onEvent: (event: ChatEvent) => void;
  /** 브라우저가 재접속을 포기했을 때(로그아웃·정지로 401 등) — 세션을 다시 확인하게 한다. */
  onLost?: () => void;
}

/** 로그인한 동안 연결 하나로 볼 수 있는 모든 방의 새 메시지·삭제를 받는다.
 *  서버가 50초마다 끊으면 브라우저가 Last-Event-ID를 실어 스스로 다시 붙는다. */
export function useChatStream(enabled: boolean, handlers: Handlers) {
  const latest = useRef(handlers);
  useEffect(() => {
    latest.current = handlers;
  });

  useEffect(() => {
    if (!enabled) return;
    let source: EventSource | null = null;
    let recover: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    const relay = (raw: MessageEvent<string>) => {
      try {
        latest.current.onEvent(JSON.parse(raw.data) as ChatEvent);
      } catch {
        // 깨진 프레임 하나 때문에 연결을 버리지 않는다
      }
    };
    const connect = () => {
      source = new EventSource(chatStreamUrl(), { withCredentials: true });
      source.addEventListener("message", relay);
      source.addEventListener("deleted", relay as EventListener);
      source.onerror = () => {
        if (stopped || source?.readyState !== EventSource.CLOSED) return;
        latest.current.onLost?.();
        recover = setTimeout(connect, STREAM_RECOVER_MS);
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(recover);
      source?.close();
    };
  }, [enabled]);
}
