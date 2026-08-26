"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";

const TABS = [
  { href: "/", label: "지도 탐색" },
  { href: "/analysis", label: "AI 분석" },
];

export function TopBar() {
  const pathname = usePathname();

  return (
    <header className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
      <div className="flex items-center gap-6">
        <span className="text-sm font-semibold text-[var(--text-primary)]">Metabole</span>
        <nav className="flex items-center gap-4">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "text-sm font-medium text-[var(--accent)]"
                    : "text-sm font-medium text-[var(--text-secondary)]"
                }
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <ThemeToggle />
    </header>
  );
}
