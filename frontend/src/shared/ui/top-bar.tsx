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
    <header className="flex shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-surface)] px-5">
      <div className="flex items-center gap-7">
        <span className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">Metabole</span>
        <nav className="flex items-center gap-1">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`border-b-2 px-2 py-3.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--accent)] ${
                  active
                    ? "border-[var(--accent)] text-[var(--accent)]"
                    : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
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
