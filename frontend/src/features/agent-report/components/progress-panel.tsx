import type { AgentName } from "@/shared/api/types";
import type { AgentState, AgentStatus } from "../lib/agent-events";
import styles from "./analysis-workspace.module.css";

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

/** 색상만으로 상태를 전달하지 않도록 스크린리더/텍스트 라벨을 함께 노출한다. */
const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: "대기",
  running: "진행 중",
  done: "완료",
  error: "오류",
};

interface ProgressPanelProps {
  state: AgentState;
}

export function ProgressPanel({ state }: ProgressPanelProps) {
  return (
    <div className={`${styles.progressPanel} border-[var(--border)]`} role="status" aria-live="polite">
      <div className={styles.panelHeading}>
        <span className={`${styles.panelNumber} text-[var(--accent)]`}>02</span>
        <h2>진행 상황</h2>
      </div>
      <ol className="flex flex-col divide-y divide-[var(--border)]">
        {AGENT_ORDER.map((name) => {
          const slot = state.agents[name];
          return (
            <li key={name} className={styles.progressItem}>
              <div className="flex items-center gap-2.5">
                <span
                  aria-hidden
                  className={`h-2 w-2 shrink-0 rounded-full transition-colors duration-300 ${DOT[slot.status]}`}
                />
                <span className="text-sm font-medium text-[var(--text-primary)]">{LABEL[name]}</span>
                <span className={`${styles.statusLabel} ml-auto text-[var(--text-secondary)]`}>{STATUS_LABEL[slot.status]}</span>
              </div>
              {slot.tools.length > 0 && (
                <ul className="mt-2 ml-1 flex flex-col gap-1 border-l border-[var(--border)] pl-3.5">
                  {slot.tools.map((t, i) => (
                    <li
                      key={`${i}:${t.tool}`}
                      className={
                        i === slot.tools.length - 1
                          ? "text-xs leading-relaxed text-[var(--text-primary)]"
                          : "text-xs leading-relaxed text-[var(--text-secondary)]"
                      }
                    >
                      <span className="font-medium">{t.tool}</span> — {t.summary}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
