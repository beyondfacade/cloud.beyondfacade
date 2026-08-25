"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiPost } from "@/shared/api/client";
import { config } from "@/shared/config";
import type { AgentEvent } from "@/shared/api/types";
import { applyAgentEvent, initialAgentState, type AgentState } from "../lib/agent-events";

export interface StartAnalysisParams {
  region: string;
  industry: string;
  question?: string;
}

const EVENT_TYPES: AgentEvent["type"][] = ["agent_status", "tool_call", "report_delta", "report_done"];

/** POST /analysis 로 분석을 시작하고 SSE 이벤트를 구독해 리듀서에 적용한다. */
export function useAgentReport() {
  const [state, setState] = useState<AgentState>(initialAgentState());
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => sourceRef.current?.close();
  }, []);

  const start = useCallback(async (params: StartAnalysisParams) => {
    sourceRef.current?.close();
    setState(initialAgentState());

    const { analysis_id } = await apiPost<{ analysis_id: string }>("/analysis", params);
    const source = new EventSource(`${config.apiBase}/analysis/${analysis_id}/events`);
    sourceRef.current = source;

    for (const type of EVENT_TYPES) {
      source.addEventListener(type, (e) => {
        const ev = JSON.parse((e as MessageEvent).data) as AgentEvent;
        setState((prev) => applyAgentEvent(prev, ev));
        if (ev.type === "report_done") {
          source.close();
        }
      });
    }

    source.onerror = () => {
      setState((prev) => ({ ...prev, error: "분석 스트림 연결에 실패했습니다." }));
      source.close();
    };
  }, []);

  return { state, start };
}
