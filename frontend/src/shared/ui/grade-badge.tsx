const LABEL: Record<"fact" | "signal", string> = {
  fact: "확인된 사실",
  signal: "참고 신호",
};

const STYLE: Record<"fact" | "signal", string> = {
  fact: "bg-[var(--accent)] text-[var(--accent-fg)]",
  signal: "border border-[var(--border)] text-[var(--text-secondary)]",
};

interface GradeBadgeProps {
  grade: "fact" | "signal";
}

export function GradeBadge({ grade }: GradeBadgeProps) {
  return (
    <span className={`inline-flex shrink-0 items-center rounded px-2 py-0.5 text-xs font-medium whitespace-nowrap ${STYLE[grade]}`}>
      {LABEL[grade]}
    </span>
  );
}
