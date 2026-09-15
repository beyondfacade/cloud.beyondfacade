"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiPost } from "@/shared/api/client";
import type { AgentEvent } from "@/shared/api/types";
import { applyAgentEvent, initialAgentState, type AgentState } from "../lib/agent-events";

export interface StartAnalysisParams {
  region: string;
  industry: string;
  question?: string;
}

const EVENT_TYPES: AgentEvent["type"][] = ["agent_status", "tool_call", "report_delta", "report_done"];

// TODO: RAG 분석 백엔드 미구현 — AI 분석 탭(분석 시작 POST + SSE)만 mock 베이스를 유지한다.
// 실 분석 API 전환 시 이 상수를 제거하고 config.apiBase로 복귀할 것.
const ANALYSIS_API_BASE = "/api/mock";

/** POST /analysis 로 분석을 시작하고 SSE 이벤트를 구독해 리듀서에 적용한다. */
export function useAgentReport() {
  const [state, setState] = useState<AgentState>(initialAgentState());
  const [loading, setLoading] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  // ref로 동기 재진입 가드 — start()가 첫 await(apiPost) 전에 즉시 체크해야 더블클릭 레이스를 막는다.
  const loadingRef = useRef(false);

  useEffect(() => {
    return () => sourceRef.current?.close();
  }, []);

  const finish = () => {
    loadingRef.current = false;
    setLoading(false);
  };

  const start = useCallback(async (params: StartAnalysisParams) => {
    if (loadingRef.current) return; // 진행 중이면 재진입 무시
    loadingRef.current = true;
    setLoading(true);

    sourceRef.current?.close();
    sourceRef.current = null;
    setState(initialAgentState());

    try {
      const { analysis_id } = await apiPost<{ analysis_id: string }>("/analysis", params, ANALYSIS_API_BASE);
      const source = new EventSource(`${ANALYSIS_API_BASE}/analysis/${analysis_id}/events`);
      sourceRef.current = source;

      for (const type of EVENT_TYPES) {
        source.addEventListener(type, (e) => {
          let ev: AgentEvent;
          try {
            ev = JSON.parse((e as MessageEvent).data) as AgentEvent;
          } catch {
            // 손상된 SSE payload — onerror와 동일한 에러 경로에 합류.
            setState((prev) => ({ ...prev, error: "분석 스트림 데이터를 해석하지 못했습니다." }));
            source.close();
            finish();
            return;
          }
          setState((prev) => applyAgentEvent(prev, ev));
          if (ev.type === "report_done") {
            source.close();
            finish();
          }
        });
      }

      source.onerror = () => {
        setState((prev) => ({ ...prev, error: "분석 스트림 연결에 실패했습니다." }));
        source.close();
        finish();
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : "분석 시작에 실패했습니다.";
      setState((prev) => ({ ...prev, error: message }));
      finish();
    }
  }, []);

  return { state, start, loading };
}
