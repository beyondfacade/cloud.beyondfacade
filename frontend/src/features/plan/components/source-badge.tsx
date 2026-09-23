/** 프리필 출처 배지 — 값 옆에 "어디서 온 값인지"를 항상 보인다(후보.md 항목 1). 단서는 title과 보조문 둘 다. */
export function SourceBadge({ label, caveat, id }: { label: string; caveat: string; id: string }) {
  return (
    <span className="flex flex-col gap-1">
      <span
        title={caveat}
        className="inline-flex w-fit items-center rounded border border-[var(--border)] bg-[var(--bg-raised)] px-1.5 py-0.5 text-[10px] font-medium tracking-wide text-[var(--text-secondary)]"
        data-source-badge
      >
        {label}
      </span>
      <small id={id} className="text-[11px] leading-snug text-[var(--text-secondary)]">{caveat}</small>
    </span>
  );
}
