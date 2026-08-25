import type { AgentName } from "@/shared/api/types";
import type { AgentState, AgentStatus } from "../lib/agent-events";

const AGENT_ORDER: AgentName[] = ["orchestrator", "market", "shock", "funding"];

const LABEL: Record<AgentName, string> = {
  orchestrator: "오케스트레이터",
  market: "상권 진단",
  shock: "충격 분석",
  funding: "정책자금",
};

const DOT: Record<AgentStatus, string> = {
  idle: "bg-[var(--border)]",
  running: "bg-[var(--warn)] animate-pulse",
  done: "bg-[var(--ok)]",
  error: "bg-[var(--danger)]",
};

interface ProgressPanelProps {
  state: AgentState;
}

export function ProgressPanel({ state }: ProgressPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      {AGENT_ORDER.map((name) => {
        const slot = state.agents[name];
        return (
          <div key={name} className="rounded border border-[var(--border)] bg-[var(--bg-surface)] p-3">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full transition-colors duration-300 ${DOT[slot.status]}`} />
              <span className="text-sm font-medium text-[var(--text-primary)]">{LABEL[name]}</span>
            </div>
            {slot.tools.length > 0 && (
              <ul className="mt-2 flex flex-col gap-1 border-l border-[var(--border)] pl-3">
                {slot.tools.map((t, i) => (
                  <li
                    key={`${t.tool}:${t.summary}`}
                    className={
                      i === slot.tools.length - 1
                        ? "text-xs text-[var(--text-primary)]"
                        : "text-xs text-[var(--text-secondary)]"
                    }
                  >
                    <span className="font-medium">{t.tool}</span> — {t.summary}
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
