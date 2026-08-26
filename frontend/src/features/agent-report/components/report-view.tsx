import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { GradeBadge } from "@/shared/ui/grade-badge";
import type { AgentState } from "../lib/agent-events";

const SECTION_ORDER = ["verdict", "market", "shock", "funding", "calculator"] as const;

interface Citation {
  title: string;
  url: string;
  grade: "fact" | "signal";
}

function isCitation(v: unknown): v is Citation {
  const c = v as Partial<Citation> | null;
  return (
    typeof c === "object" &&
    c !== null &&
    typeof c.title === "string" &&
    typeof c.url === "string" &&
    (c.grade === "fact" || c.grade === "signal")
  );
}

interface ReportViewProps {
  state: AgentState;
}

export function ReportView({ state }: ReportViewProps) {
  const sections = SECTION_ORDER.filter((s) => state.sections[s]);

  if (sections.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] px-6 py-12 text-center">
        <span className="text-sm font-medium text-[var(--text-primary)]">아직 리포트가 없습니다</span>
        <span className="max-w-sm text-sm leading-relaxed text-[var(--text-secondary)]">
          지역 코드와 업종을 확인한 뒤 [분석 시작]을 누르면, 에이전트가 수집한 근거와 함께 리포트가 여기에 채워집니다.
        </span>
      </div>
    );
  }

  const citations = state.citations.filter(isCitation);

  return (
    <div className="flex flex-col gap-7">
      {sections.map((section) => (
        <section key={section} className="report-markdown text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{state.sections[section]}</ReactMarkdown>
        </section>
      ))}
      {state.done && citations.length > 0 && (
        <div className="border-t border-[var(--border)] pt-5">
          <h3 className="text-xs font-semibold tracking-wide text-[var(--text-secondary)]">참고 자료</h3>
          <ul className="mt-3 flex flex-col divide-y divide-[var(--border)]">
            {citations.map((c) => (
              <li key={`${c.title}:${c.url}`} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer"
                  className="min-w-0 text-[var(--accent)] underline decoration-[var(--border)] underline-offset-4 transition-colors hover:decoration-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  {c.title}
                </a>
                <GradeBadge grade={c.grade} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
