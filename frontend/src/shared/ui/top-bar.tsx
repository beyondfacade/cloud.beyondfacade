"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";
import styles from "./top-bar.module.css";

const TABS = [
  { href: "/map", label: "지도 탐색" },
  { href: "/analysis", label: "AI 분석" },
];

export function TopBar() {
  const pathname = usePathname();
  if (pathname === "/") return null;

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/" className={styles.brand} aria-label="Metabole">
          <span className={styles.mark} aria-hidden="true">m.</span>
          <span className={styles.wordmark}>Metabole<small>서울 상권 아틀라스</small></span>
        </Link>
        <nav className={styles.navigation} aria-label="주요 메뉴">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                prefetch={false}
                aria-current={active ? "page" : undefined}
                className={styles.tab}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
        <div className={styles.theme}><ThemeToggle /></div>
      </div>
    </header>
  );
}
