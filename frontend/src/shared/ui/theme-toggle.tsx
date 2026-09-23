"use client";
import { useCallback, useEffect, useSyncExternalStore } from "react";

const STORAGE_KEY = "metabole-theme";

function getTheme(): "light" | "dark" {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function subscribe(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}

/** localStorage에 저장된 테마를 data-theme에 반영 (클라이언트 마운트 시). */
export function ThemeToggle() {
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "dark" || saved === "light") {
      document.documentElement.dataset.theme = saved;
    }
  }, []);

  const theme = useSyncExternalStore(subscribe, getTheme, () => "light");
  const toggle = useCallback(() => {
    const next = getTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(STORAGE_KEY, next);
  }, []);
  return (
    <button aria-label="테마 전환" onClick={toggle}
      className="rounded-md border border-[var(--border)] px-2.5 py-1 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px">
      {theme === "dark" ? "라이트" : "다크"}
    </button>
  );
}
