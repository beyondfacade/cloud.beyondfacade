"use client";
import { useCallback, useSyncExternalStore } from "react";

function getTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}
function subscribe(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getTheme, () => "light");
  const toggle = useCallback(() => {
    document.documentElement.dataset.theme = getTheme() === "dark" ? "light" : "dark";
  }, []);
  return (
    <button aria-label="테마 전환" onClick={toggle}
      className="rounded-md border border-[var(--border)] px-2.5 py-1 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px">
      {theme === "dark" ? "라이트" : "다크"}
    </button>
  );
}
