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
    return <p className="text-sm text-[var(--text-secondary)]">분석을 시작하면 리포트가 여기에 표시됩니다</p>;
  }

  const citations = state.citations.filter(isCitation);

  return (
    <div className="flex flex-col gap-6">
      {sections.map((section) => (
        <div key={section} className="text-sm text-[var(--text-primary)]">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{state.sections[section]}</ReactMarkdown>
        </div>
      ))}
      {state.done && citations.length > 0 && (
        <div className="border-t border-[var(--border)] pt-4">
          <h3 className="text-sm font-medium text-[var(--text-primary)]">참고 자료</h3>
          <ul className="mt-2 flex flex-col gap-2">
            {citations.map((c, i) => (
              <li key={i} className="flex items-center justify-between gap-2 text-sm">
                <a href={c.url} target="_blank" rel="noreferrer" className="text-[var(--accent)] underline">
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
