/** 라우트 셸의 Suspense 폴백 — 스트리밍 중 빈 화면 대신 레이아웃 높이를 유지한다. */
export function RouteFallback({ label }: { label: string }) {
  return (
    <div className="flex flex-1 items-center justify-center" role="status" aria-live="polite">
      <span className="text-sm text-[var(--text-secondary)]">{label}…</span>
    </div>
  );
}
